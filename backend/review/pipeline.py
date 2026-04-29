"""Review pipeline: orchestrates multi-model review of a PR."""

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger("uvicorn")

from provider.interface import ChatMessage, LLMProvider
from provider.registry import ProviderRegistry

from .consensus import ConsensusEngine
from .github_adapter import GitHubAdapter
from .models import PRReview, ReviewFinding


_REVIEW_SYSTEM_PROMPT = """\
You are an expert code reviewer. Analyze the provided diff and find real issues.

Return a JSON array of findings. Each finding has:
- file_path: string
- line_number: int (approximate)
- severity: "critical" | "high" | "medium" | "low" | "style"
- category: "security" | "bug" | "performance" | "style" | "architecture"
- title: short title
- description: detailed explanation
- suggestion: how to fix it

Only report real, actionable issues. If the code looks fine, return [].
Return ONLY the JSON array, no other text."""


def _parse_findings(raw: str, provider: str) -> list[ReviewFinding]:
    """Parse LLM output into ReviewFinding objects."""
    text = raw.strip()
    if "```" in text:
        start = text.find("[")
        end = text.rfind("]")
        if start != -1 and end != -1:
            text = text[start : end + 1]
    try:
        items = json.loads(text)
    except json.JSONDecodeError:
        return []
    findings = []
    for item in items:
        try:
            finding = ReviewFinding(
                id=str(uuid.uuid4())[:8],
                file_path=item.get("file_path", "unknown"),
                line_number=item.get("line_number", 0),
                severity=item.get("severity", "medium"),
                category=item.get("category", "bug"),
                title=item.get("title", "Unknown issue"),
                description=item.get("description", ""),
                suggestion=item.get("suggestion", ""),
                providers_agreed=[provider],
            )
            findings.append(finding)
        except Exception:
            continue
    return findings


class ReviewPipeline:
    """Orchestrates multi-model code review for a PR."""

    def __init__(
        self,
        registry: ProviderRegistry,
        github: GitHubAdapter,
        consensus: Optional[ConsensusEngine] = None,
        review_models: Optional[list[str]] = None,
    ) -> None:
        self._registry = registry
        self._github = github
        self._consensus = consensus or ConsensusEngine(min_agreement=2)
        self._review_models = review_models or ["openai", "anthropic"]

    async def _review_with_provider(
        self, provider: LLMProvider, diff: str, model: str
    ) -> list[ReviewFinding]:
        """Run a single provider's review on a diff."""
        messages = [
            ChatMessage(role="system", content=_REVIEW_SYSTEM_PROMPT),
            ChatMessage(role="user", content=f"Review this diff:\n\n{diff}"),
        ]
        response = await provider.chat(messages, model=model, temperature=0.2)
        return _parse_findings(response.content, provider.name)

    async def review_pr(self, repo: str, pr_number: int) -> PRReview:
        """Run the full review pipeline on a PR."""
        import asyncio

        review_id = str(uuid.uuid4())[:12]
        now = datetime.now(timezone.utc).isoformat()

        pr_info = await self._github.get_pr_info(repo, pr_number)
        diff = await self._github.get_pr_diff(repo, pr_number)
        head_sha = pr_info.get("head", {}).get("sha", "")

        review = PRReview(
            id=review_id,
            repo=repo,
            pr_number=pr_number,
            pr_title=pr_info.get("title", ""),
            pr_author=pr_info.get("user", {}).get("login", ""),
            status="reviewing",
            started_at=now,
        )

        # Collect findings from each provider in parallel
        model_results: dict[str, list[ReviewFinding]] = {}
        models_used: list[str] = []
        total_cost = 0.0

        async def _run_provider(name: str) -> tuple[str, list[ReviewFinding]]:
            provider = self._registry.get(name)
            if provider is None:
                logger.warning(f"[Review] Provider '{name}' not found, skipping")
                return name, []
            config = self._registry.get_provider_config(name)
            model = config.get("default_model", "")
            logger.info(f"[Review] Running review with {name} (model={model})")
            try:
                findings = await self._review_with_provider(provider, diff, model)
                logger.info(f"[Review] {name} returned {len(findings)} findings")
                return name, findings
            except Exception as e:
                logger.error(f"[Review] {name} failed: {e}")
                return name, []

        tasks = [_run_provider(name) for name in self._review_models]
        results = await asyncio.gather(*tasks)

        for name, findings in results:
            models_used.append(name)
            if findings:
                model_results[name] = findings

        # Run consensus
        consensus_findings = self._consensus.find_consensus(model_results)

        # Post to GitHub
        if consensus_findings:
            for finding in consensus_findings[:50]:
                try:
                    await self._github.post_review_comment(
                        repo, pr_number, head_sha, finding
                    )
                except Exception:
                    pass

            summary = self._build_summary(consensus_findings, len(self._review_models))
            try:
                await self._github.post_review_summary(repo, pr_number, summary)
            except Exception:
                pass

        return review.model_copy(
            update={
                "status": "completed",
                "findings": consensus_findings,
                "models_used": models_used,
                "cost_usd": total_cost,
                "completed_at": datetime.now(timezone.utc).isoformat(),
                "summary": self._build_summary(consensus_findings, len(self._review_models)),
            }
        )

    def _build_summary(self, findings: list[ReviewFinding], total_models: int) -> str:
        """Generate a human-readable review summary."""
        if not findings:
            return "No consensus issues found. All models agree the code looks good."

        severity_counts: dict[str, int] = {}
        for f in findings:
            severity_counts[f.severity] = severity_counts.get(f.severity, 0) + 1

        lines = [
            "## Code Review Summary",
            "",
            f"**{len(findings)} issues** found by consensus of {total_models} models:",
            "",
        ]
        for sev in ["critical", "high", "medium", "low", "style"]:
            count = severity_counts.get(sev, 0)
            if count:
                lines.append(f"- **{sev.upper()}**: {count}")

        lines.append("")
        lines.append(
            "_Only issues agreed upon by multiple models are shown "
            "to reduce false positives._"
        )
        return "\n".join(lines)
