from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import os
import secrets

import jwt
from sqlalchemy.orm import Session, selectinload

from ..models.all_models import Role, SystemConfig, User


ROLE_OWNER = "owner"
ROLE_WAREHOUSE = "warehouse_operator"
ROLE_SALES = "sales_clerk"
ALL_ROLE_CODES = {ROLE_OWNER, ROLE_WAREHOUSE, ROLE_SALES}
PASSWORD_ITERATIONS = 310_000


class AuthenticationConfigurationError(RuntimeError):
    pass


def is_standalone_mode(db: Session) -> bool:
    config = db.query(SystemConfig).filter(SystemConfig.key == "standalone_mode").first()
    return config is None or config.value.strip().lower() in {"1", "true", "yes", "on"}


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt.encode("ascii"), PASSWORD_ITERATIONS
    ).hex()
    return f"pbkdf2_sha256${PASSWORD_ITERATIONS}${salt}${digest}"


def verify_password(password: str, password_hash: str) -> bool:
    try:
        algorithm, iterations, salt, expected = password_hash.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        actual = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), salt.encode("ascii"), int(iterations)
        ).hex()
    except (TypeError, ValueError):
        return False
    return hmac.compare_digest(actual, expected)


def _jwt_secret() -> str:
    secret = os.getenv("SELLHELP_JWT_SECRET")
    if not secret or len(secret) < 32:
        raise AuthenticationConfigurationError(
            "SELLHELP_JWT_SECRET must contain at least 32 characters before disabling standalone mode"
        )
    return secret


def role_codes(user: User) -> list[str]:
    return sorted(role.code for role in user.roles)


def user_payload(user: User, standalone_mode: bool = False) -> dict:
    return {
        "id": user.id,
        "username": user.username,
        "display_name": user.display_name,
        "role_codes": role_codes(user),
        "standalone_mode": standalone_mode,
    }


def standalone_payload() -> dict:
    return {
        "id": None,
        "username": "standalone",
        "display_name": "Standalone operator",
        "role_codes": [ROLE_OWNER],
        "standalone_mode": True,
    }


def find_user(db: Session, username: str) -> User | None:
    return (
        db.query(User)
        .options(selectinload(User.roles))
        .filter(User.username == username)
        .first()
    )


def issue_access_token(user: User) -> str:
    now = datetime.now(timezone.utc)
    expires = now + timedelta(minutes=int(os.getenv("SELLHELP_JWT_EXPIRE_MINUTES", "480")))
    return jwt.encode(
        {
            "sub": str(user.id),
            "ver": user.auth_version,
            "iat": now,
            "exp": expires,
            "jti": secrets.token_urlsafe(16),
        },
        _jwt_secret(),
        algorithm="HS256",
    )


def user_from_token(db: Session, token: str) -> User | None:
    try:
        claims = jwt.decode(token, _jwt_secret(), algorithms=["HS256"])
        user_id = int(claims["sub"])
        token_version = int(claims["ver"])
    except (jwt.PyJWTError, KeyError, TypeError, ValueError, AuthenticationConfigurationError):
        return None

    user = (
        db.query(User)
        .options(selectinload(User.roles))
        .filter(User.id == user_id, User.is_active.is_(True))
        .first()
    )
    if user is None or user.auth_version != token_version:
        return None
    return user


def assign_roles(db: Session, codes: list[str]) -> list[Role]:
    roles = db.query(Role).filter(Role.code.in_(codes)).all()
    if len(roles) != len(set(codes)):
        raise ValueError("One or more role codes are invalid")
    return roles
