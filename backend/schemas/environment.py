"""Pydantic schemas for Environment (v3.0)."""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class EnvironmentCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)
    description: Optional[str] = None
    is_default: bool = False


class EnvironmentResponse(BaseModel):
    id: UUID
    name: str
    description: Optional[str] = None
    is_default: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class EnvironmentListResponse(BaseModel):
    items: list[EnvironmentResponse]
    total: int
