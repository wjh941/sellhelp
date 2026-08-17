import re

from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from .database import SessionLocal
from .services.audit_service import record_audit
from .services.auth_service import (
    ALL_ROLE_CODES,
    ROLE_OWNER,
    ROLE_SALES,
    ROLE_WAREHOUSE,
    is_standalone_mode,
    standalone_payload,
    user_from_token,
    user_payload,
)


SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}
PUBLIC_PATHS = {"/api/health", "/api/auth/login"}
OWNER_PREFIXES = ("/api/system", "/api/export", "/api/audit-logs", "/api/auth/users", "/api/auth/roles")
WAREHOUSE_WRITES = (
    ("POST", re.compile(r"^/api/purchase-orders/?$")),
    ("POST", re.compile(r"^/api/returns/?$")),
    ("POST", re.compile(r"^/api/stock-takes/(?:prepare|confirm)$")),
)
SALES_WRITES = (
    ("POST", re.compile(r"^/api/sales-orders/?$")),
    ("POST", re.compile(r"^/api/sales-orders/\d+/(?:pay|complete-payment)$")),
    ("POST", re.compile(r"^/api/customers/\d+/pay$")),
    ("POST", re.compile(r"^/api/finance/customer/\d+/repay$")),
    ("POST", re.compile(r"^/api/finance/batch-repay$")),
)


def allowed_roles(method: str, path: str) -> set[str]:
    if path in {"/api/auth/me", "/api/auth/logout"}:
        return ALL_ROLE_CODES
    if path.startswith(OWNER_PREFIXES):
        return {ROLE_OWNER}
    for allowed_method, pattern in WAREHOUSE_WRITES:
        if method == allowed_method and pattern.fullmatch(path):
            return {ROLE_OWNER, ROLE_WAREHOUSE}
    for allowed_method, pattern in SALES_WRITES:
        if method == allowed_method and pattern.fullmatch(path):
            return {ROLE_OWNER, ROLE_SALES}
    if method in SAFE_METHODS:
        return ALL_ROLE_CODES
    return {ROLE_OWNER}


def is_sensitive(method: str, path: str) -> bool:
    return method not in SAFE_METHODS or path.startswith(OWNER_PREFIXES)


class PermissionMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        path = request.url.path
        method = request.method
        if not path.startswith("/api") or method == "OPTIONS" or path in PUBLIC_PATHS:
            return await call_next(request)

        session_factory = getattr(request.app.state, "auth_session_factory", None)
        db = session_factory() if session_factory else SessionLocal()
        close_session = session_factory is None
        try:
            if is_standalone_mode(db):
                identity = standalone_payload()
            else:
                authorization = request.headers.get("Authorization", "")
                token = authorization.removeprefix("Bearer ").strip() if authorization.startswith("Bearer ") else ""
                user = user_from_token(db, token) if token else None
                if user is None:
                    return JSONResponse(status_code=401, content={"detail": "Authentication required"})
                identity = user_payload(user)

            required_roles = allowed_roles(method, path)
            if not required_roles.intersection(identity["role_codes"]):
                if is_sensitive(method, path):
                    record_audit(
                        db,
                        user_id=identity["id"],
                        client_ip=request.client.host if request.client else None,
                        operation_type="access_denied",
                        operation_detail=f"{method} {path}",
                        status_code=403,
                    )
                return JSONResponse(status_code=403, content={"detail": "Permission denied"})

            request.state.auth_user = identity
            response = await call_next(request)
            if is_sensitive(method, path):
                record_audit(
                    db,
                    user_id=identity["id"],
                    client_ip=request.client.host if request.client else None,
                    operation_type="request",
                    operation_detail=f"{method} {path}",
                    status_code=response.status_code,
                )
            return response
        finally:
            if close_session:
                db.close()
