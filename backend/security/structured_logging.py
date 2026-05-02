"""Structured logging with request_id and secret sanitization — OPT-42.

Provides:
- request_id middleware for FastAPI
- Structured log formatter with request context
- Secret sanitization for log output
- Helper for adding structured context to log records
"""

from __future__ import annotations

import logging
import re
import time
import uuid
from contextvars import ContextVar

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

# Context variable for request_id, available across async tasks
request_id_ctx: ContextVar[str] = ContextVar("request_id", default="")

# Patterns to sanitize from log messages
_SENSITIVE_PATTERNS = [
    re.compile(r'(Bearer\s+)\S+', re.IGNORECASE),
    re.compile(r'(X-Service-Token[:\s]+)\S+', re.IGNORECASE),
    re.compile(r'(api_key["\s:=]+)\S+', re.IGNORECASE),
    re.compile(r'(token["\s:=]+)\S+', re.IGNORECASE),
    re.compile(r'(password["\s:=]+)\S+', re.IGNORECASE),
    re.compile(r'(secret["\s:=]+)\S+', re.IGNORECASE),
]

_REDACTED = "[REDACTED]"


def sanitize_log_value(value: str) -> str:
    """Remove sensitive data from a log string."""
    result = value
    for pattern in _SENSITIVE_PATTERNS:
        result = pattern.sub(rf'\g<1>{_REDACTED}', result)
    return result


class StructuredFormatter(logging.Formatter):
    """Log formatter that includes request context fields."""

    def format(self, record: logging.LogRecord) -> str:
        parts = [
            f"ts={self.formatTime(record, self.datefmt)}",
            f"level={record.levelname}",
            f"logger={record.name}",
            f"msg={sanitize_log_value(record.getMessage())}",
        ]

        req_id = request_id_ctx.get("")
        if req_id:
            parts.append(f"request_id={req_id}")

        for field in ("actor_type", "actor_id", "run_id", "workflow_id",
                       "connector_id", "path", "method", "status_code", "duration_ms"):
            value = getattr(record, field, None)
            if value is not None:
                parts.append(f"{field}={sanitize_log_value(str(value))}")

        if record.exc_info and record.exc_info[0] is not None:
            parts.append(f"exc={self.formatException(record.exc_info)}")

        return " | ".join(parts)


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Middleware that injects request_id into every request and logs structured access info."""

    async def dispatch(self, request: Request, call_next) -> Response:
        req_id = request.headers.get("X-Request-ID", "") or uuid.uuid4().hex[:8]
        request_id_ctx.set(req_id)

        start = time.monotonic()
        path = request.url.path
        method = request.method
        actor_type, actor_id = _extract_actor(request)

        response = None
        try:
            response = await call_next(request)
            return response
        except Exception:
            logger = logging.getLogger("request")
            logger.error(
                "Unhandled exception",
                extra={"path": path, "method": method, "actor_type": actor_type, "actor_id": actor_id},
                exc_info=True,
            )
            raise
        finally:
            duration_ms = round((time.monotonic() - start) * 1000, 1)
            status_code = response.status_code if response else 500

            if response:
                response.headers["X-Request-ID"] = req_id

            if not path.startswith(("/health", "/sse", "/connections")):
                logger = logging.getLogger("access")
                log_level = logging.WARNING if status_code >= 500 else (
                    logging.INFO if status_code >= 400 else logging.DEBUG
                )
                logger.log(
                    log_level,
                    f"{method} {path} -> {status_code}",
                    extra={
                        "path": path,
                        "method": method,
                        "status_code": status_code,
                        "duration_ms": duration_ms,
                        "actor_type": actor_type,
                        "actor_id": actor_id,
                    },
                )


def _extract_actor(request: Request) -> tuple[str, str]:
    """Extract actor info from request without decoding JWT."""
    if request.headers.get("X-Service-Token"):
        return "service", "service"
    if request.headers.get("Authorization", "").startswith("Bearer "):
        return "authenticated", "jwt-user"
    header_role = request.headers.get("X-User-Role", "")
    if header_role:
        return "header", header_role
    return "anonymous", ""


def setup_logging(level: int = logging.INFO) -> None:
    """Configure application-wide structured logging."""
    formatter = StructuredFormatter()
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)

    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
