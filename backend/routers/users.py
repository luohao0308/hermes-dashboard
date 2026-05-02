"""User and Team Management API — v3.0 Enterprise.

Endpoints:
    GET    /api/teams              — list teams
    POST   /api/teams              — create team
    GET    /api/teams/{id}         — get team
    DELETE /api/teams/{id}         — delete team
    GET    /api/users               — list users
    POST   /api/users               — create user
    GET    /api/users/{id}          — get user
    PUT    /api/users/{id}          — update user
    DELETE /api/users/{id}          — delete user
"""

from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from database import get_db
from models import User, Team
from schemas.user import (
    TeamCreate,
    TeamResponse,
    TeamListResponse,
    UserCreate,
    UserUpdate,
    UserResponse,
    UserListResponse,
)
from security.audit import write_audit_log
from security.rbac import require_role

router = APIRouter(tags=["users"])


# ---------------------------------------------------------------------------
# Teams
# ---------------------------------------------------------------------------


@router.get("/api/teams", response_model=TeamListResponse)
def list_teams(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    total = db.query(Team).count()
    items = db.query(Team).order_by(Team.created_at.desc()).offset(offset).limit(limit).all()
    return TeamListResponse(
        items=[TeamResponse.model_validate(t) for t in items],
        total=total,
    )


@router.post("/api/teams", response_model=TeamResponse, status_code=201)
def create_team(
    body: TeamCreate,
    db: Session = Depends(get_db),
    _role: str = Depends(require_role("admin")),
):
    existing = db.query(Team).filter(Team.name == body.name).first()
    if existing:
        raise HTTPException(status_code=409, detail="Team name already exists")

    team = Team(
        id=uuid.uuid4(),
        name=body.name,
        description=body.description,
    )
    db.add(team)
    db.flush()

    write_audit_log(
        db,
        actor_type="user",
        actor_id="api",
        action="team.created",
        resource_type="team",
        resource_id=str(team.id),
        after_json={"name": body.name},
    )
    db.commit()
    db.refresh(team)
    return TeamResponse.model_validate(team)


@router.get("/api/teams/{team_id}", response_model=TeamResponse)
def get_team(team_id: uuid.UUID, db: Session = Depends(get_db)):
    team = db.get(Team, team_id)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    return TeamResponse.model_validate(team)


@router.delete("/api/teams/{team_id}", status_code=204)
def delete_team(
    team_id: uuid.UUID,
    db: Session = Depends(get_db),
    _role: str = Depends(require_role("admin")),
):
    team = db.get(Team, team_id)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    write_audit_log(
        db,
        actor_type="user",
        actor_id="api",
        action="team.deleted",
        resource_type="team",
        resource_id=str(team.id),
        before_json={"name": team.name},
    )
    db.delete(team)
    db.commit()


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------


@router.get("/api/users", response_model=UserListResponse)
def list_users(
    team_id: Optional[uuid.UUID] = None,
    role: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    query = db.query(User)
    if team_id is not None:
        query = query.filter(User.team_id == team_id)
    if role is not None:
        query = query.filter(User.role == role)

    total = query.count()
    items = query.order_by(User.created_at.desc()).offset(offset).limit(limit).all()
    return UserListResponse(
        items=[UserResponse.model_validate(u) for u in items],
        total=total,
    )


@router.post("/api/users", response_model=UserResponse, status_code=201)
def create_user(
    body: UserCreate,
    db: Session = Depends(get_db),
    _role: str = Depends(require_role("admin")),
):
    existing = db.query(User).filter(User.email == body.email).first()
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")

    if body.team_id:
        team = db.get(Team, body.team_id)
        if not team:
            raise HTTPException(status_code=404, detail="Team not found")

    user = User(
        id=uuid.uuid4(),
        email=body.email,
        display_name=body.display_name,
        team_id=body.team_id,
        role=body.role or "viewer",
        is_active=True,
    )
    db.add(user)
    db.flush()

    write_audit_log(
        db,
        actor_type="user",
        actor_id="api",
        action="user.created",
        resource_type="user",
        resource_id=str(user.id),
        after_json={"email": body.email, "role": user.role},
    )
    db.commit()
    db.refresh(user)
    return UserResponse.model_validate(user)


@router.get("/api/users/{user_id}", response_model=UserResponse)
def get_user(user_id: uuid.UUID, db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return UserResponse.model_validate(user)


@router.put("/api/users/{user_id}", response_model=UserResponse)
def update_user(
    user_id: uuid.UUID,
    body: UserUpdate,
    db: Session = Depends(get_db),
    _role: str = Depends(require_role("admin")),
):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    before = {"display_name": user.display_name, "role": user.role, "is_active": user.is_active}

    if body.display_name is not None:
        user.display_name = body.display_name
    if body.role is not None:
        user.role = body.role
    if body.is_active is not None:
        user.is_active = body.is_active
    if body.team_id is not None:
        if body.team_id:
            team = db.get(Team, body.team_id)
            if not team:
                raise HTTPException(status_code=404, detail="Team not found")
        user.team_id = body.team_id

    db.flush()

    write_audit_log(
        db,
        actor_type="user",
        actor_id="api",
        action="user.updated",
        resource_type="user",
        resource_id=str(user.id),
        before_json=before,
        after_json={"display_name": user.display_name, "role": user.role, "is_active": user.is_active},
    )
    db.commit()
    db.refresh(user)
    return UserResponse.model_validate(user)


@router.delete("/api/users/{user_id}", status_code=204)
def delete_user(
    user_id: uuid.UUID,
    db: Session = Depends(get_db),
    _role: str = Depends(require_role("admin")),
):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    write_audit_log(
        db,
        actor_type="user",
        actor_id="api",
        action="user.deleted",
        resource_type="user",
        resource_id=str(user.id),
        before_json={"email": user.email, "role": user.role},
    )
    db.delete(user)
    db.commit()
