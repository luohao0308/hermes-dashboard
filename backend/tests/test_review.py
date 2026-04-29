"""Unit tests for the review pipeline."""

import json
import pytest
from pathlib import Path

from review.models import ReviewFinding, PRReview
from review.consensus import ConsensusEngine, _title_similarity
from review.pipeline import _parse_findings
from review.review_store import ReviewStore


# ---------------------------------------------------------------------------
# ReviewFinding / PRReview models
# ---------------------------------------------------------------------------


class TestReviewFinding:
    def test_create(self):
        f = ReviewFinding(
            id="abc", file_path="app.py", line_number=42,
            severity="high", category="bug", title="Null deref",
            description="Possible null pointer", suggestion="Add check",
            confidence=0.8, providers_agreed=["openai"],
        )
        assert f.severity == "high"
        assert f.providers_agreed == ["openai"]

    def test_defaults(self):
        f = ReviewFinding(
            id="x", file_path="a.py", line_number=1,
            severity="low", category="style", title="t", description="d",
        )
        assert f.suggestion == ""
        assert f.confidence == 1.0
        assert f.providers_agreed == []


class TestPRReview:
    def test_create(self):
        r = PRReview(
            id="r1", repo="org/repo", pr_number=10,
            pr_title="Fix bug", pr_author="alice",
        )
        assert r.status == "pending"
        assert r.findings == []


# ---------------------------------------------------------------------------
# _title_similarity
# ---------------------------------------------------------------------------


class TestTitleSimilarity:
    def test_identical(self):
        assert _title_similarity("SQL injection", "SQL injection") == 1.0

    def test_similar(self):
        assert _title_similarity("SQL injection risk", "SQL injection vulnerability") > 0.5

    def test_different(self):
        assert _title_similarity("SQL injection", "Performance issue") < 0.3


# ---------------------------------------------------------------------------
# ConsensusEngine
# ---------------------------------------------------------------------------


class TestConsensusEngine:
    def _make_finding(self, title: str, file: str = "app.py", line: int = 10):
        return ReviewFinding(
            id=title[:8], file_path=file, line_number=line,
            severity="high", category="bug", title=title, description="",
        )

    def test_no_agreement(self):
        engine = ConsensusEngine(min_agreement=2)
        results = {
            "openai": [self._make_finding("SQL injection")],
            "anthropic": [self._make_finding("Performance issue")],
        }
        assert engine.find_consensus(results) == []

    def test_two_models_agree(self):
        engine = ConsensusEngine(min_agreement=2)
        results = {
            "openai": [self._make_finding("SQL injection in login")],
            "anthropic": [self._make_finding("SQL injection in login handler")],
        }
        findings = engine.find_consensus(results)
        assert len(findings) == 1
        assert findings[0].confidence == 1.0
        assert set(findings[0].providers_agreed) == {"openai", "anthropic"}

    def test_different_file_not_matched(self):
        engine = ConsensusEngine(min_agreement=2)
        results = {
            "openai": [self._make_finding("SQL injection", file="a.py")],
            "anthropic": [self._make_finding("SQL injection", file="b.py")],
        }
        assert engine.find_consensus(results) == []

    def test_different_line_not_matched(self):
        engine = ConsensusEngine(min_agreement=2, line_proximity=5)
        results = {
            "openai": [self._make_finding("SQL injection", line=10)],
            "anthropic": [self._make_finding("SQL injection", line=50)],
        }
        assert engine.find_consensus(results) == []

    def test_three_models_partial_agreement(self):
        engine = ConsensusEngine(min_agreement=2)
        results = {
            "openai": [self._make_finding("Null dereference")],
            "anthropic": [self._make_finding("Null dereference")],
            "ollama": [self._make_finding("Type error in parser")],
        }
        findings = engine.find_consensus(results)
        assert len(findings) == 1
        assert findings[0].confidence == round(2 / 3, 2)

    def test_severity_sorting(self):
        engine = ConsensusEngine(min_agreement=2)
        f_style = self._make_finding("Style issue", line=1).model_copy(update={"severity": "style"})
        f_crit = self._make_finding("Security hole", line=10).model_copy(update={"severity": "critical"})
        results = {
            "openai": [f_style, f_crit],
            "anthropic": [f_style, f_crit],
        }
        findings = engine.find_consensus(results)
        assert findings[0].severity == "critical"


# ---------------------------------------------------------------------------
# _parse_findings
# ---------------------------------------------------------------------------


class TestParseFindings:
    def test_valid_json(self):
        raw = json.dumps([
            {
                "file_path": "app.py", "line_number": 10,
                "severity": "high", "category": "bug",
                "title": "Null deref", "description": "desc", "suggestion": "fix",
            }
        ])
        findings = _parse_findings(raw, "openai")
        assert len(findings) == 1
        assert findings[0].file_path == "app.py"
        assert findings[0].providers_agreed == ["openai"]

    def test_markdown_code_block(self):
        raw = '```json\n[{"file_path":"a.py","line_number":1,"severity":"low","category":"style","title":"t","description":"d"}]\n```'
        findings = _parse_findings(raw, "test")
        assert len(findings) == 1

    def test_empty_array(self):
        assert _parse_findings("[]", "test") == []

    def test_invalid_json(self):
        assert _parse_findings("not json", "test") == []


# ---------------------------------------------------------------------------
# ReviewStore
# ---------------------------------------------------------------------------


class TestReviewStore:
    def test_save_and_get(self, tmp_path):
        store = ReviewStore(db_path=tmp_path / "test.db")
        review = PRReview(
            id="r1", repo="org/repo", pr_number=5,
            pr_title="Fix", pr_author="bob", status="completed",
            findings=[
                ReviewFinding(
                    id="f1", file_path="a.py", line_number=10,
                    severity="high", category="bug", title="Bug", description="desc",
                )
            ],
            cost_usd=0.05,
            models_used=["openai"],
            started_at="2026-01-01T00:00:00Z",
            completed_at="2026-01-01T00:01:00Z",
            summary="Found 1 issue",
        )
        store.save(review)
        loaded = store.get("r1")
        assert loaded is not None
        assert loaded.repo == "org/repo"
        assert len(loaded.findings) == 1
        assert loaded.findings[0].title == "Bug"

    def test_list_reviews(self, tmp_path):
        store = ReviewStore(db_path=tmp_path / "test.db")
        for i in range(3):
            store.save(PRReview(
                id=f"r{i}", repo="org/repo", pr_number=i,
                pr_title=f"PR {i}", pr_author="alice",
                started_at=f"2026-01-0{i+1}T00:00:00Z",
            ))
        reviews = store.list_reviews()
        assert len(reviews) == 3

    def test_list_filter_by_repo(self, tmp_path):
        store = ReviewStore(db_path=tmp_path / "test.db")
        store.save(PRReview(id="r1", repo="a/repo", pr_number=1, pr_title="A", pr_author="x", started_at="2026-01-01T00:00:00Z"))
        store.save(PRReview(id="r2", repo="b/repo", pr_number=2, pr_title="B", pr_author="y", started_at="2026-01-02T00:00:00Z"))
        reviews = store.list_reviews(repo="a/repo")
        assert len(reviews) == 1
        assert reviews[0].repo == "a/repo"

    def test_get_stats(self, tmp_path):
        store = ReviewStore(db_path=tmp_path / "test.db")
        store.save(PRReview(id="r1", repo="a/repo", pr_number=1, pr_title="A", pr_author="x", status="completed", cost_usd=0.10, started_at="2026-01-01T00:00:00Z"))
        store.save(PRReview(id="r2", repo="a/repo", pr_number=2, pr_title="B", pr_author="y", status="pending", started_at="2026-01-02T00:00:00Z"))
        stats = store.get_stats()
        assert stats["total_reviews"] == 2
        assert stats["completed_reviews"] == 1
        assert stats["average_cost_usd"] == 0.10

    def test_get_nonexistent(self, tmp_path):
        store = ReviewStore(db_path=tmp_path / "test.db")
        assert store.get("nope") is None
