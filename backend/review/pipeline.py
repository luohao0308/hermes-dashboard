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
        cost_tracker=None,
    ) -> None:
        self._registry = registry
        self._github = github
        self._consensus = consensus or ConsensusEngine(min_agreement=2)
        self._review_models = review_models or ["openai", "anthropic"]
        self._cost_tracker = cost_tracker

    async def _review_with_provider(
        self, provider: LLMProvider, diff: str, model: str
    ) -> tuple[list[ReviewFinding], int, int]:
        """Run a single provider's review on a diff. Returns (findings, input_tokens, output_tokens)."""
        messages = [
            ChatMessage(role="system", content=_REVIEW_SYSTEM_PROMPT),
            ChatMessage(role="user", content=f"Review this diff:\n\n{diff}"),
        ]
        response = await provider.chat(messages, model=model, temperature=0.2)
        findings = _parse_findings(response.content, provider.name)
        return findings, response.input_tokens, response.output_tokens

    async def review_pr(self, repo: str, pr_number: int) -> PRReview:
        """Run the full review pipeline on a PR."""
        import asyncio

        review_id = str(uuid.uuid4())[:12]
        now = datetime.now(timezone.utc).isoformat()

        pr_info = await self._github.get_pr_info(repo, pr_number)
        diff = await self._github.get_pr_diff(repo, pr_number)
        head_sha = pr_info.get("head", {}).get("sha", "")
        diff_lines = len(diff.splitlines())

        logger.info(f"[Review] Starting review {review_id} for {repo}#{pr_number}")
        logger.info(f"[Review] PR: {pr_info.get('title', '')}")
        logger.info(f"[Review] Author: {pr_info.get('user', {}).get('login', '')}")
        logger.info(f"[Review] Diff: {diff_lines} lines, {len(diff)} chars")
        logger.info(f"[Review] Models: {self._review_models}")

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
        total_input_tokens = 0
        total_output_tokens = 0

        async def _run_provider(name: str) -> tuple[str, list[ReviewFinding], int, int]:
            provider = self._registry.get(name)
            if provider is None:
                logger.warning(f"[Review] Provider '{name}' not found, skipping")
                return name, [], 0, 0
            config = self._registry.get_provider_config(name)
            model = config.get("default_model", "")
            logger.info(f"[Review] Calling {name} (model={model})...")
            try:
                findings, input_tokens, output_tokens = await self._review_with_provider(provider, diff, model)
                logger.info(f"[Review] {name} done: {len(findings)} findings, {input_tokens} in/{output_tokens} out tokens")
                return name, findings, input_tokens, output_tokens
            except Exception as e:
                logger.error(f"[Review] {name} failed: {e}")
                return name, [], 0, 0

        tasks = [_run_provider(name) for name in self._review_models]
        results = await asyncio.gather(*tasks)

        for name, findings, in_tokens, out_tokens in results:
            models_used.append(name)
            total_input_tokens += in_tokens
            total_output_tokens += out_tokens
            if findings:
                model_results[name] = findings
            # Record cost
            if self._cost_tracker and (in_tokens > 0 or out_tokens > 0):
                provider_config = self._registry.get_provider_config(name)
                cost_1k_in = 0.0
                cost_1k_out = 0.0
                for m in provider_config.get("models", []):
                    if m.get("id") == provider_config.get("default_model", ""):
                        cost_1k_in = m.get("cost_per_1k_input", 0.0)
                        cost_1k_out = m.get("cost_per_1k_output", 0.0)
                        break
                self._cost_tracker.record_usage(
                    provider=name,
                    model=provider_config.get("default_model", ""),
                    input_tokens=in_tokens,
                    output_tokens=out_tokens,
                    cost_per_1k_input=cost_1k_in,
                    cost_per_1k_output=cost_1k_out,
                    review_id=review_id,
                )
                cost = (in_tokens / 1000 * cost_1k_in) + (out_tokens / 1000 * cost_1k_out)
                total_cost += cost

        # Run consensus
        consensus_findings = self._consensus.find_consensus(model_results)

        # Build review log
        logger.info(f"[Review] ═══════════════════════════════════════")
        logger.info(f"[Review] 审查完成: {repo}#{pr_number}")
        logger.info(f"[Review] PR 标题: {pr_info.get('title', '')}")
        logger.info(f"[Review] 使用模型: {', '.join(models_used)}")
        logger.info(f"[Review] Token 用量: {total_input_tokens} 输入 / {total_output_tokens} 输出")
        logger.info(f"[Review] 成本: ${total_cost:.6f}")
        logger.info(f"[Review] 发现问题: {len(consensus_findings)} 个")
        if consensus_findings:
            for i, f in enumerate(consensus_findings[:10], 1):
                logger.info(f"[Review]   [{f.severity.upper()}] {f.title} ({f.file_path}:{f.line_number})")
            if len(consensus_findings) > 10:
                logger.info(f"[Review]   ... 还有 {len(consensus_findings) - 10} 个问题")
        else:
            logger.info(f"[Review] 所有模型一致认为代码没有问题")
        logger.info(f"[Review] ═══════════════════════════════════════")

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
                "cost_usd": round(total_cost, 6),
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
