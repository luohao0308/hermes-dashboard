"""Auth API — v3.0 Enterprise.

Endpoints:
    POST /api/auth/login  — authenticate and return JWT
    POST /api/auth/logout — client-side token discard (stateless)
    GET  /api/auth/me     — return current user info
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session

from database import get_db
from models.user import User
from security.auth import (
    create_access_token,
    get_current_user,
    verify_password,
)
from security.audit import write_audit_log

router = APIRouter(prefix="/api/auth", tags=["auth"])
limiter = Limiter(key_func=get_remote_address)


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------


class LoginRequest(BaseModel):
    email: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    email: str
    role: str


class MeResponse(BaseModel):
    user_id: str
    email: str
    display_name: str
    role: str
    is_active: bool


# ---------------------------------------------------------------------------
# POST /api/auth/login
# ---------------------------------------------------------------------------


@router.post("/login", response_model=LoginResponse)
@limiter.limit("10/minute")
def login(request: Request, body: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == body.email).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not user.password_hash or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token(user_id=str(user.id), role=user.role)

    write_audit_log(
        db,
        actor_type="user",
        actor_id=str(user.id),
        action="auth.login",
        resource_type="user",
        resource_id=str(user.id),
    )
    db.commit()

    return LoginResponse(
        access_token=token,
        user_id=str(user.id),
        email=user.email,
        role=user.role,
    )


# ---------------------------------------------------------------------------
# POST /api/auth/logout
# ---------------------------------------------------------------------------


@router.post("/logout")
def logout(
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    write_audit_log(
        db,
        actor_type="user",
        actor_id=user["user_id"],
        action="auth.logout",
        resource_type="user",
        resource_id=user["user_id"],
    )
    db.commit()
    return {"message": "Logged out"}


# ---------------------------------------------------------------------------
# GET /api/auth/me
# ---------------------------------------------------------------------------


@router.get("/me", response_model=MeResponse)
def get_me(
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    db_user = db.query(User).filter(User.id == user["user_id"]).first()
    if not db_user:
        # Service account or header-based user without DB record
        return MeResponse(
            user_id=user["user_id"],
            email=user.get("email", ""),
            display_name=user.get("email", user["user_id"]),
            role=user["role"],
            is_active=True,
        )
    return MeResponse(
        user_id=str(db_user.id),
        email=db_user.email,
        display_name=db_user.display_name,
        role=db_user.role,
        is_active=db_user.is_active,
    )
