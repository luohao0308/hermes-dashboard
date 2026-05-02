"""Shared worker heartbeat write/read helpers.

Centralizes heartbeat file paths and staleness logic so that
health.py, metrics.py, and the workers themselves all use the
same configuration and classification rules.

Heartbeat files contain JSON with metadata::

    {"ts": "2026-05-01T12:00:00+00:00",
     "worker_id": "worker-abcd1234",
     "pid": 12345,
     "version": "3.0.0"}

Backward compatible: plain ISO timestamp strings are still accepted.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone

from config import settings

# Mapping from canonical worker name -> config-driven file path
_WORKER_PATHS: dict[str, str] = {
    "scheduler_worker": settings.scheduler_heartbeat_path,
    "retention_worker": settings.retention_heartbeat_path,
}

# Also accept hyphenated names (used by /health endpoint)
_WORKER_PATHS["scheduler-worker"] = settings.scheduler_heartbeat_path
_WORKER_PATHS["retention-worker"] = settings.retention_heartbeat_path

_STALE_SECONDS = settings.worker_heartbeat_stale_seconds


def write_heartbeat(
    worker_name: str,
    *,
    worker_id: str | None = None,
    pid: int | None = None,
    version: str | None = None,
) -> None:
    """Write heartbeat JSON to the file for *worker_name*.

    Includes worker_id, pid, and version when provided so that health
    endpoints can report which instance is running.  Silently ignores
    OS errors (disk full, permissions) so the worker loop never crashes
    because of monitoring bookkeeping.
    """
    path = _WORKER_PATHS.get(worker_name)
    if path is None:
        return
    payload: dict = {"ts": datetime.now(timezone.utc).isoformat()}
    if worker_id is not None:
        payload["worker_id"] = worker_id
    if pid is not None:
        payload["pid"] = pid
    if version is not None:
        payload["version"] = version
    try:
        with open(path, "w") as fh:
            fh.write(json.dumps(payload))
    except OSError:
        pass


def _parse_heartbeat_content(raw: str) -> dict:
    """Parse heartbeat file content — JSON or legacy plain timestamp."""
    raw = raw.strip()
    if not raw:
        return {}
    if raw.startswith("{"):
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, ValueError):
            return {}
    # Legacy format: plain ISO timestamp string
    return {"ts": raw}


def read_heartbeat(worker_name: str) -> dict:
    """Read the heartbeat file and return a status dict.

    Returns::

        {"status": "alive"|"stale"|"missing"|"error",
         "age_seconds": int|None,
         "worker_id": str|None,
         "pid": int|None,
         "version": str|None,
         "error": str|None}   # only when status == "error"
    """
    path = _WORKER_PATHS.get(worker_name)
    if path is None:
        return {"status": "missing", "age_seconds": None, "worker_id": None, "pid": None, "version": None}
    try:
        mtime = os.path.getmtime(path)
        age = round(datetime.now(timezone.utc).timestamp() - mtime)

        # Read file content for metadata
        worker_id = None
        pid = None
        version = None
        try:
            with open(path) as fh:
                meta = _parse_heartbeat_content(fh.read())
            worker_id = meta.get("worker_id")
            pid = meta.get("pid")
            version = meta.get("version")
        except OSError:
            pass

        return {
            "status": "alive" if age < _STALE_SECONDS else "stale",
            "age_seconds": age,
            "worker_id": worker_id,
            "pid": pid,
            "version": version,
        }
    except FileNotFoundError:
        return {"status": "missing", "age_seconds": None, "worker_id": None, "pid": None, "version": None}
    except Exception as exc:
        return {"status": "error", "age_seconds": None, "worker_id": None, "pid": None, "version": None, "error": str(exc)[:100]}


def read_all_workers() -> dict[str, dict]:
    """Read heartbeats for all known workers. Returns a dict keyed by
    canonical (underscore) worker name."""
    return {
        name: read_heartbeat(name)
        for name in ("scheduler_worker", "retention_worker")
    }
