"""SQLite storage for review history and audit trail."""

import json
import sqlite3
from pathlib import Path
from typing import Optional

from .models import PRReview, ReviewFinding

_DB_PATH = Path(__file__).parent.parent / "data" / "reviews.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS reviews (
    id TEXT PRIMARY KEY,
    repo TEXT NOT NULL,
    pr_number INTEGER NOT NULL,
    pr_title TEXT NOT NULL,
    pr_author TEXT NOT NULL,
    status TEXT NOT NULL,
    findings_json TEXT NOT NULL,
    cost_usd REAL NOT NULL DEFAULT 0.0,
    models_used_json TEXT NOT NULL,
    started_at TEXT NOT NULL,
    completed_at TEXT,
    summary TEXT
);

CREATE INDEX IF NOT EXISTS idx_reviews_repo ON reviews(repo);
CREATE INDEX IF NOT EXISTS idx_reviews_status ON reviews(status);
CREATE INDEX IF NOT EXISTS idx_reviews_started ON reviews(started_at);
"""


class ReviewStore:
    """Persists PR review results to SQLite."""

    def __init__(self, db_path: Optional[Path] = None) -> None:
        self._db_path = db_path or _DB_PATH
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(str(self._db_path)) as conn:
            conn.executescript(_SCHEMA)

    def save(self, review: PRReview) -> None:
        """Insert or update a review."""
        with sqlite3.connect(str(self._db_path)) as conn:
            conn.execute(
                """INSERT OR REPLACE INTO reviews
                   (id, repo, pr_number, pr_title, pr_author, status,
                    findings_json, cost_usd, models_used_json,
                    started_at, completed_at, summary)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    review.id,
                    review.repo,
                    review.pr_number,
                    review.pr_title,
                    review.pr_author,
                    review.status,
                    json.dumps([f.model_dump() for f in review.findings]),
                    review.cost_usd,
                    json.dumps(review.models_used),
                    review.started_at,
                    review.completed_at,
                    review.summary,
                ),
            )

    def get(self, review_id: str) -> Optional[PRReview]:
        """Get a review by ID."""
        with sqlite3.connect(str(self._db_path)) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM reviews WHERE id = ?", (review_id,)
            ).fetchone()
        if row is None:
            return None
        return self._row_to_review(row)

    def list_reviews(
        self,
        repo: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[PRReview]:
        """List reviews with optional filters."""
        query = "SELECT * FROM reviews WHERE 1=1"
        params: list = []
        if repo:
            query += " AND repo = ?"
            params.append(repo)
        if status:
            query += " AND status = ?"
            params.append(status)
        query += " ORDER BY started_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        with sqlite3.connect(str(self._db_path)) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(query, params).fetchall()
        return [self._row_to_review(r) for r in rows]

    def get_stats(self) -> dict:
        """Get aggregate review statistics."""
        with sqlite3.connect(str(self._db_path)) as conn:
            total = conn.execute("SELECT COUNT(*) FROM reviews").fetchone()[0]
            completed = conn.execute(
                "SELECT COUNT(*) FROM reviews WHERE status = 'completed'"
            ).fetchone()[0]
            avg_cost = conn.execute(
                "SELECT AVG(cost_usd) FROM reviews WHERE status = 'completed'"
            ).fetchone()[0] or 0.0
        return {
            "total_reviews": total,
            "completed_reviews": completed,
            "average_cost_usd": round(avg_cost, 4),
        }

    @staticmethod
    def _row_to_review(row: sqlite3.Row) -> PRReview:
        findings_data = json.loads(row["findings_json"])
        findings = [ReviewFinding(**f) for f in findings_data]
        return PRReview(
            id=row["id"],
            repo=row["repo"],
            pr_number=row["pr_number"],
            pr_title=row["pr_title"],
            pr_author=row["pr_author"],
            status=row["status"],
            findings=findings,
            cost_usd=row["cost_usd"],
            models_used=json.loads(row["models_used_json"]),
            started_at=row["started_at"],
            completed_at=row["completed_at"],
            summary=row["summary"] or "",
        )
