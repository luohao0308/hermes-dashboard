"""Authentication module — JWT tokens, password hashing, current-user dependency.

Auth flow:
- POST /api/auth/login — email+password -> JWT access token
- GET  /api/auth/me     — returns current user from token
- POST /api/auth/logout — client discards token (stateless)

Production: JWT token required on all protected endpoints.
Dev/Test: X-User-Role header fallback allowed when ENVIRONMENT != production.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
from fastapi import Depends, HTTPException, Request
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from config import settings
from database import get_db
from models.user import User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ---------------------------------------------------------------------------
# Password helpers
# ---------------------------------------------------------------------------


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


# ---------------------------------------------------------------------------
# JWT helpers
# ---------------------------------------------------------------------------


def create_access_token(
    user_id: str,
    role: str,
    expires_delta: Optional[timedelta] = None,
) -> str:
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.jwt_expire_minutes)
    )
    payload = {
        "sub": user_id,
        "role": role,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


# ---------------------------------------------------------------------------
# Current-user dependency
# ---------------------------------------------------------------------------


def _get_valid_service_tokens() -> set[str]:
    """Parse configured service tokens from settings."""
    raw = settings.service_tokens
    if not raw:
        return set()
    return {t.strip() for t in raw.split(",") if t.strip()}


def validate_service_token(token: str) -> bool:
    """Check if a token is a valid service token."""
    return token in _get_valid_service_tokens()


def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
) -> dict:
    """Extract current user from JWT token or service token.

    Returns dict with keys: user_id, role, email.
    Checks in order: X-Service-Token header, Authorization Bearer JWT,
    X-User-Role header (dev/test only).
    """
    # 1. Service token (for machine-to-machine calls)
    service_token = request.headers.get("X-Service-Token", "")
    if service_token and validate_service_token(service_token):
        return {"user_id": "service", "role": "operator", "email": ""}

    # 2. JWT token
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        # Check if it's a service token passed as Bearer
        if validate_service_token(token):
            return {"user_id": "service", "role": "operator", "email": ""}
        payload = decode_access_token(token)
        user_id = payload.get("sub")
        role = payload.get("role", "viewer")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token payload")
        return {"user_id": user_id, "role": role, "email": payload.get("email", "")}

    # 3. Dev/test fallback: X-User-Role header
    if settings.environment != "production":
        header_role = request.headers.get("X-User-Role")
        if header_role:
            return {"user_id": "dev-header-user", "role": header_role, "email": ""}

    raise HTTPException(status_code=401, detail="Not authenticated")


def get_optional_user(
    request: Request,
    db: Session = Depends(get_db),
) -> Optional[dict]:
    """Like get_current_user but returns None instead of raising 401."""
    try:
        return get_current_user(request, db)
    except HTTPException:
        return None


def require_auth(required_role: str):
    """FastAPI dependency combining authentication + role check.

    Usage:
        @router.post("/...", dependencies=[Depends(require_auth("operator"))])
    """
    from security.rbac import ROLE_HIERARCHY

    required_level = ROLE_HIERARCHY.get(required_role, 999)

    def dependency(
        request: Request,
        db: Session = Depends(get_db),
    ) -> dict:
        user = get_current_user(request, db)
        user_level = ROLE_HIERARCHY.get(user["role"], -1)
        if user_level < required_level:
            raise HTTPException(
                status_code=403,
                detail=f"Insufficient permissions: requires {required_role}, has {user['role']}",
            )
        return user

    return dependency
