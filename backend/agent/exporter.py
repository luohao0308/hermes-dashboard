"""Local Markdown export helpers for RCA and runbooks."""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import Any


def build_session_export(session_id: str, rca: dict[str, Any] | None, runbook: dict[str, Any] | None) -> str:
    lines = [
        f"# Hermès Session {session_id[:8]}",
        "",
        f"- Session: `{session_id}`",
        f"- Exported: {datetime.now().isoformat()}",
        "",
    ]
    if rca:
        lines.extend([
            "## RCA",
            "",
            f"- Root cause: {rca.get('root_cause')}",
            f"- Confidence: {round(float(rca.get('confidence') or 0) * 100)}%",
            "",
            "### Evidence",
            "",
        ])
        for item in rca.get("evidence", [])[:8]:
            lines.append(f"- [{item.get('source')}] {item.get('title')}: {item.get('detail')}")
        lines.append("")
    if runbook:
        lines.extend([
            "## Runbook",
            "",
            runbook.get("markdown") or runbook.get("summary") or "No runbook content.",
            "",
        ])
    if not rca and not runbook:
        lines.append("No RCA or runbook has been generated yet.")
    return "\n".join(lines).strip() + "\n"


def save_markdown_export(export_dir: str, session_id: str, content: str) -> dict[str, Any]:
    directory = Path(export_dir).expanduser().resolve()
    directory.mkdir(parents=True, exist_ok=True)
    filename = f"hermes-session-{_slug(session_id)}-{datetime.now().strftime('%Y%m%d-%H%M%S')}.md"
    path = directory / filename
    path.write_text(content, encoding="utf-8")
    return {
        "path": str(path),
        "filename": filename,
        "bytes": path.stat().st_size,
    }


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9_.-]+", "-", value).strip("-")
    return slug[:80] or "session"
