"""PostgreSQL-backed review repository.

Wraps the existing PRReview/ReviewFinding models from the review module.
Uses per-operation sessions to avoid long-lived session accumulation.
"""

from __future__ import annotations

import json
import uuid
from typing import Any, Callable, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from models.review import ReviewRow
from repositories.base import ReviewRepository


class PgReviewRepository(ReviewRepository):
    """PostgreSQL implementation of ReviewRepository."""

    def __init__(self, session_factory: Callable[[], Session]) -> None:
        self._session_factory = session_factory

    def _run_in_session(self, fn, *, read_only: bool = False):
        db = self._session_factory()
        try:
            result = fn(db)
            if not read_only:
                db.commit()
            return result
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def save(self, review: Any) -> None:
        def _save(db: Session) -> None:
            findings_data = [f.model_dump() for f in review.findings]
            row = ReviewRow(
                id=uuid.UUID(review.id) if isinstance(review.id, str) else review.id,
                repo=review.repo,
                pr_number=review.pr_number,
                pr_title=review.pr_title,
                pr_author=review.pr_author,
                status=review.status,
                findings_json=json.dumps(findings_data),
                cost_usd=review.cost_usd,
                models_used_json=json.dumps(review.models_used),
                started_at=review.started_at,
                completed_at=review.completed_at,
                summary=review.summary,
            )
            db.merge(row)
        self._run_in_session(_save)

    def get(self, review_id: str) -> Optional[Any]:
        def _get(db: Session) -> Optional[Any]:
            row = db.get(ReviewRow, uuid.UUID(review_id))
            return _row_to_review(row) if row else None
        return self._run_in_session(_get, read_only=True)

    def list_reviews(
        self,
        repo: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Any]:
        def _list(db: Session) -> list[Any]:
            q = db.query(ReviewRow)
            if repo:
                q = q.filter(ReviewRow.repo == repo)
            if status:
                q = q.filter(ReviewRow.status == status)
            rows = q.order_by(ReviewRow.started_at.desc()).offset(offset).limit(limit).all()
            return [_row_to_review(r) for r in rows]
        return self._run_in_session(_list, read_only=True)

    def get_stats(self) -> dict[str, Any]:
        def _stats(db: Session) -> dict[str, Any]:
            total = db.query(func.count(ReviewRow.id)).scalar() or 0
            completed = db.query(func.count(ReviewRow.id)).filter(ReviewRow.status == "completed").scalar() or 0
            avg_cost = db.query(func.avg(ReviewRow.cost_usd)).filter(ReviewRow.status == "completed").scalar() or 0.0
            return {
                "total_reviews": total,
                "completed_reviews": completed,
                "average_cost_usd": round(float(avg_cost), 4),
            }
        return self._run_in_session(_stats, read_only=True)


def _row_to_review(row: ReviewRow) -> Any:
    from review.models import PRReview, ReviewFinding

    findings_data = json.loads(row.findings_json)
    findings = [ReviewFinding(**f) for f in findings_data]
    return PRReview(
        id=str(row.id),
        repo=row.repo,
        pr_number=row.pr_number,
        pr_title=row.pr_title,
        pr_author=row.pr_author,
        status=row.status,
        findings=findings,
        cost_usd=row.cost_usd,
        models_used=json.loads(row.models_used_json),
        started_at=row.started_at,
        completed_at=row.completed_at,
        summary=row.summary or "",
    )
