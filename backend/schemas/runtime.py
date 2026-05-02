"""Pydantic schemas for Runtime API."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class RuntimeCreate(BaseModel):
    """Request body for POST /api/runtimes."""

    name: str = Field(..., min_length=1, max_length=255, description="Runtime name, e.g. 'github-reviewer'")
    type: str = Field("custom", max_length=50, description="Runtime type: agent, connector, custom")
    status: str = Field("active", max_length=20, description="Runtime status: active, paused, archived")
    config_json: Optional[dict[str, Any]] = Field(None, description="Arbitrary runtime configuration")


class RuntimeUpdate(BaseModel):
    """Request body for PATCH /api/runtimes/{runtime_id}."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    type: Optional[str] = Field(None, max_length=50)
    status: Optional[str] = Field(None, max_length=20)
    config_json: Optional[dict[str, Any]] = None


class RuntimeResponse(BaseModel):
    """Response model for a single Runtime."""

    id: UUID
    name: str
    type: str
    status: str
    config_json: Optional[dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
