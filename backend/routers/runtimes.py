"""Runtime API — minimal CRUD for workflow runtimes.

Endpoints:
    GET  /api/runtimes           — list all runtimes
    POST /api/runtimes           — create a runtime
"""

from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from database import get_db
from models import Runtime
from schemas.runtime import RuntimeCreate, RuntimeResponse
from security.rbac import require_role

router = APIRouter(prefix="/api/runtimes", tags=["runtimes"])


# ---------------------------------------------------------------------------
# GET /api/runtimes
# ---------------------------------------------------------------------------

@router.get("", response_model=list[RuntimeResponse])
def list_runtimes(
    status: Optional[str] = Query(None, description="Filter by status: active, paused, archived"),
    db: Session = Depends(get_db),
):
    query = db.query(Runtime)
    if status is not None:
        query = query.filter(Runtime.status == status)
    runtimes = query.order_by(Runtime.created_at.desc()).all()
    return [RuntimeResponse.model_validate(r) for r in runtimes]


# ---------------------------------------------------------------------------
# POST /api/runtimes
# ---------------------------------------------------------------------------

@router.post("", response_model=RuntimeResponse, status_code=201)
def create_runtime(
    body: RuntimeCreate,
    db: Session = Depends(get_db),
    _role: str = Depends(require_role("operator")),
):
    runtime = Runtime(
        id=uuid.uuid4(),
        name=body.name,
        type=body.type,
        status=body.status,
        config_json=body.config_json,
    )
    db.add(runtime)
    db.commit()
    db.refresh(runtime)
    return RuntimeResponse.model_validate(runtime)
