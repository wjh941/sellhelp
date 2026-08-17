from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session, selectinload

from ..database import get_db
from ..models.all_models import AuditLog, Role, User
from ..schemas.all_schemas import (
    AuditLogPageResponse,
    AuthUserResponse,
    LoginRequest,
    LoginResponse,
    RoleResponse,
    UserCreateRequest,
    UserUpdateRequest,
)
from ..services.audit_service import record_audit
from ..services.auth_service import (
    AuthenticationConfigurationError,
    assign_roles,
    find_user,
    hash_password,
    is_standalone_mode,
    issue_access_token,
    standalone_payload,
    user_payload,
    verify_password,
)


router = APIRouter(prefix="/api/auth", tags=["Authentication"])
audit_router = APIRouter(prefix="/api", tags=["Audit logs"])


@router.post("/login", response_model=LoginResponse)
def login(data: LoginRequest, request: Request, db: Session = Depends(get_db)):
    if is_standalone_mode(db):
        return {**standalone_payload(), "access_token": None}

    user = find_user(db, data.username)
    if user is None or not verify_password(data.password, user.password_hash):
        record_audit(
            db,
            user_id=None,
            client_ip=request.client.host if request.client else None,
            operation_type="login_failed",
            operation_detail=f"username={data.username}",
            status_code=401,
        )
        raise HTTPException(status_code=401, detail="Invalid username or password")
    try:
        token = issue_access_token(user)
    except AuthenticationConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    record_audit(
        db,
        user_id=user.id,
        client_ip=request.client.host if request.client else None,
        operation_type="login",
        operation_detail="Successful login",
        status_code=200,
    )
    return {**user_payload(user), "access_token": token}


@router.post("/logout")
def logout(request: Request, db: Session = Depends(get_db)):
    identity = request.state.auth_user
    if identity["id"] is not None:
        user = db.query(User).filter(User.id == identity["id"]).first()
        if user is not None:
            user.auth_version += 1
            db.commit()
    return {"message": "Logged out"}


@router.get("/me", response_model=AuthUserResponse)
def me(request: Request):
    return request.state.auth_user


@router.get("/roles", response_model=list[RoleResponse])
def list_roles(db: Session = Depends(get_db)):
    return db.query(Role).order_by(Role.code).all()


@router.get("/users", response_model=list[AuthUserResponse])
def list_users(db: Session = Depends(get_db)):
    users = db.query(User).options(selectinload(User.roles)).order_by(User.username).all()
    return [user_payload(user) for user in users]


@router.post("/users", response_model=AuthUserResponse, status_code=status.HTTP_201_CREATED)
def create_user(data: UserCreateRequest, db: Session = Depends(get_db)):
    if find_user(db, data.username):
        raise HTTPException(status_code=409, detail="Username already exists")
    try:
        roles = assign_roles(db, data.role_codes)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    user = User(
        username=data.username,
        display_name=data.display_name,
        password_hash=hash_password(data.password),
        roles=roles,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user_payload(user)


@router.put("/users/{user_id}", response_model=AuthUserResponse)
def update_user(user_id: int, data: UserUpdateRequest, db: Session = Depends(get_db)):
    user = db.query(User).options(selectinload(User.roles)).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    if data.display_name is not None:
        user.display_name = data.display_name
    if data.password is not None:
        user.password_hash = hash_password(data.password)
        user.auth_version += 1
    if data.role_codes is not None:
        try:
            user.roles = assign_roles(db, data.role_codes)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        user.auth_version += 1
    if data.is_active is not None:
        user.is_active = data.is_active
        user.auth_version += 1
    db.commit()
    db.refresh(user)
    return user_payload(user)


@audit_router.get("/audit-logs", response_model=AuditLogPageResponse)
def list_audit_logs(
    operation_type: str | None = None,
    user_id: int | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    query = db.query(AuditLog).options(selectinload(AuditLog.user))
    if operation_type:
        query = query.filter(AuditLog.operation_type == operation_type)
    if user_id:
        query = query.filter(AuditLog.user_id == user_id)
    total = query.count()
    records = query.order_by(AuditLog.timestamp.desc(), AuditLog.id.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return {
        "items": [
            {
                "id": record.id,
                "user_id": record.user_id,
                "username": record.user.username if record.user else None,
                "timestamp": record.timestamp,
                "client_ip": record.client_ip,
                "operation_type": record.operation_type,
                "operation_detail": record.operation_detail,
                "status_code": record.status_code,
            }
            for record in records
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }
