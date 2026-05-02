"""Pydantic schemas for User and Team (v3.0)."""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


# --- Team ---

class TeamCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None


class TeamResponse(BaseModel):
    id: UUID
    name: str
    description: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TeamListResponse(BaseModel):
    items: list[TeamResponse]
    total: int


# --- User ---

class UserCreate(BaseModel):
    email: str = Field(..., max_length=255)
    display_name: str = Field(..., min_length=1, max_length=100)
    password: Optional[str] = Field(None, max_length=255)
    team_id: Optional[UUID] = None
    role: str = Field("viewer", pattern=r"^(admin|operator|viewer)$")


class UserUpdate(BaseModel):
    display_name: Optional[str] = Field(None, max_length=100)
    team_id: Optional[UUID] = None
    role: Optional[str] = Field(None, pattern=r"^(admin|operator|viewer)$")
    is_active: Optional[bool] = None


class UserResponse(BaseModel):
    id: UUID
    email: str
    display_name: str
    is_active: bool
    team_id: Optional[UUID] = None
    role: str
    sso_provider: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class UserListResponse(BaseModel):
    items: list[UserResponse]
    total: int
