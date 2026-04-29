"""GitHub API adapter for fetching PR diffs and posting review comments."""

import os
from typing import Optional

import httpx

from .models import ReviewFinding


class GitHubAdapter:
    """Interacts with GitHub REST API for code review operations."""

    def __init__(self, token: Optional[str] = None) -> None:
        self._token = token or os.environ.get("GITHUB_TOKEN", "")
        self._base = "https://api.github.com"
        self._client = httpx.AsyncClient(
            base_url=self._base,
            headers={
                "Authorization": f"token {self._token}",
                "Accept": "application/vnd.github.v3+json",
            },
            timeout=30.0,
        )

    async def list_pulls(
        self, repo: str, state: str = "open", limit: int = 20
    ) -> list[dict]:
        """List pull requests for a repo."""
        resp = await self._client.get(
            f"/repos/{repo}/pulls",
            params={"state": state, "per_page": limit, "sort": "updated", "direction": "desc"},
        )
        resp.raise_for_status()
        return resp.json()

    async def get_pr_info(self, repo: str, pr_number: int) -> dict:
        """Get PR metadata."""
        resp = await self._client.get(f"/repos/{repo}/pulls/{pr_number}")
        resp.raise_for_status()
        return resp.json()

    async def get_pr_diff(self, repo: str, pr_number: int) -> str:
        """Get the unified diff for a PR."""
        resp = await self._client.get(
            f"/repos/{repo}/pulls/{pr_number}",
            headers={"Accept": "application/vnd.github.v3.diff"},
        )
        resp.raise_for_status()
        return resp.text

    async def get_pr_files(self, repo: str, pr_number: int) -> list[dict]:
        """Get list of files changed in a PR."""
        resp = await self._client.get(
            f"/repos/{repo}/pulls/{pr_number}/files",
            params={"per_page": 100},
        )
        resp.raise_for_status()
        return resp.json()

    async def get_file_content(
        self, repo: str, path: str, ref: str
    ) -> str:
        """Get file content at a specific ref."""
        resp = await self._client.get(
            f"/repos/{repo}/contents/{path}",
            params={"ref": ref},
            headers={"Accept": "application/vnd.github.v3.raw"},
        )
        resp.raise_for_status()
        return resp.text

    async def post_review_comment(
        self,
        repo: str,
        pr_number: int,
        commit_sha: str,
        finding: ReviewFinding,
    ) -> dict:
        """Post a single inline review comment on a PR."""
        body = (
            f"**[{finding.severity.upper()}] {finding.category}: {finding.title}**\n\n"
            f"{finding.description}\n\n"
        )
        if finding.suggestion:
            body += f"**Suggestion:** {finding.suggestion}\n\n"
        body += (
            f"_Confidence: {finding.confidence:.0%} | "
            f"Agreed by: {', '.join(finding.providers_agreed)}_"
        )
        resp = await self._client.post(
            f"/repos/{repo}/pulls/{pr_number}/comments",
            json={
                "body": body,
                "commit_id": commit_sha,
                "path": finding.file_path,
                "position": finding.line_number,
            },
        )
        resp.raise_for_status()
        return resp.json()

    async def post_review_summary(
        self,
        repo: str,
        pr_number: int,
        summary: str,
        event: str = "COMMENT",
    ) -> dict:
        """Post a top-level review with summary."""
        resp = await self._client.post(
            f"/repos/{repo}/pulls/{pr_number}/reviews",
            json={"body": summary, "event": event},
        )
        resp.raise_for_status()
        return resp.json()

    async def close(self) -> None:
        await self._client.aclose()
