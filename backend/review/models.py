"""Data models for the review pipeline."""

from typing import Optional

from pydantic import BaseModel, Field


class ReviewFinding(BaseModel):
    """A single issue found during code review."""

    id: str
    file_path: str
    line_number: int
    severity: str = Field(description="critical | high | medium | low | style")
    category: str = Field(description="security | bug | performance | style | architecture")
    title: str
    description: str
    suggestion: str = ""
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    providers_agreed: list[str] = Field(default_factory=list)


class PRReview(BaseModel):
    """A completed review of a pull request."""

    id: str
    repo: str
    pr_number: int
    pr_title: str
    pr_author: str
    status: str = Field(default="pending", description="pending | reviewing | completed | failed")
    findings: list[ReviewFinding] = Field(default_factory=list)
    cost_usd: float = 0.0
    models_used: list[str] = Field(default_factory=list)
    started_at: str = ""
    completed_at: Optional[str] = None
    summary: str = ""
