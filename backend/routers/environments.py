"""Environment Management API — v3.0 Enterprise.

Endpoints:
    GET    /api/environments       — list environments
    POST   /api/environments       — create environment
    GET    /api/environments/{id}   — get environment
    DELETE /api/environments/{id}   — delete environment
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from database import get_db
from models import Environment
from schemas.environment import (
    EnvironmentCreate,
    EnvironmentResponse,
    EnvironmentListResponse,
)
from security.audit import write_audit_log
from security.rbac import require_role

router = APIRouter(prefix="/api/environments", tags=["environments"])


@router.get("", response_model=EnvironmentListResponse)
def list_environments(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    total = db.query(Environment).count()
    items = (
        db.query(Environment)
        .order_by(Environment.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return EnvironmentListResponse(
        items=[EnvironmentResponse.model_validate(e) for e in items],
        total=total,
    )


@router.post("", response_model=EnvironmentResponse, status_code=201)
def create_environment(
    body: EnvironmentCreate,
    db: Session = Depends(get_db),
    _role: str = Depends(require_role("admin")),
):
    existing = db.query(Environment).filter(Environment.name == body.name).first()
    if existing:
        raise HTTPException(status_code=409, detail="Environment name already exists")

    env = Environment(
        id=uuid.uuid4(),
        name=body.name,
        description=body.description,
        is_default=body.is_default or False,
    )
    db.add(env)
    db.flush()

    write_audit_log(
        db,
        actor_type="user",
        actor_id="api",
        action="environment.created",
        resource_type="environment",
        resource_id=str(env.id),
        after_json={"name": body.name},
    )
    db.commit()
    db.refresh(env)
    return EnvironmentResponse.model_validate(env)


@router.get("/{environment_id}", response_model=EnvironmentResponse)
def get_environment(environment_id: uuid.UUID, db: Session = Depends(get_db)):
    env = db.get(Environment, environment_id)
    if not env:
        raise HTTPException(status_code=404, detail="Environment not found")
    return EnvironmentResponse.model_validate(env)


@router.delete("/{environment_id}", status_code=204)
def delete_environment(
    environment_id: uuid.UUID,
    db: Session = Depends(get_db),
    _role: str = Depends(require_role("admin")),
):
    env = db.get(Environment, environment_id)
    if not env:
        raise HTTPException(status_code=404, detail="Environment not found")

    write_audit_log(
        db,
        actor_type="user",
        actor_id="api",
        action="environment.deleted",
        resource_type="environment",
        resource_id=str(env.id),
        before_json={"name": env.name},
    )
    db.delete(env)
    db.commit()
