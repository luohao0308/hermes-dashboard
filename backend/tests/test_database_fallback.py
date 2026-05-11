"""Database startup behavior tests."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path


def test_primary_database_failure_requires_explicit_sqlite_fallback():
    backend_dir = Path(__file__).resolve().parents[1]
    env = os.environ.copy()
    env["DATABASE_URL"] = "postgresql://postgres:postgres@127.0.0.1:1/hermes_unavailable"
    env.pop("ENABLE_SQLITE_FALLBACK", None)

    result = subprocess.run(
        [sys.executable, "-c", "import database"],
        cwd=backend_dir,
        env=env,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )

    assert result.returncode != 0
    assert "ENABLE_SQLITE_FALLBACK=true" in result.stderr


def test_sqlite_fallback_initializes_local_runtime_database(tmp_path):
    backend_dir = Path(__file__).resolve().parents[1]
    isolated_backend = tmp_path / "backend"
    shutil.copytree(
        backend_dir,
        isolated_backend,
        ignore=shutil.ignore_patterns(
            "venv",
            "data",
            "__pycache__",
            ".pytest_cache",
        ),
    )
    env = os.environ.copy()
    env["DATABASE_URL"] = "postgresql://postgres:postgres@127.0.0.1:1/hermes_unavailable"
    env["ENABLE_SQLITE_FALLBACK"] = "true"
    env["PYTHONPATH"] = str(isolated_backend)

    script = """
import shutil
from pathlib import Path

import database
from sqlalchemy import text

assert database.engine.dialect.name == "sqlite"
assert database.FALLBACK_SQLITE_PATH.exists()
with database.engine.connect() as conn:
    version = conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
assert version == database.FALLBACK_ALEMBIC_VERSION
database.engine.dispose()
"""

    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=isolated_backend,
        env=env,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )

    assert result.returncode == 0, result.stderr
