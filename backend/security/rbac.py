"""Role-Based Access Control (RBAC) for v3.0 Enterprise.

Three roles: admin, operator, viewer.
- admin: full access to all resources
- operator: read/write on workflows, connectors, evals, approvals — no user/team management
- viewer: read-only on all resources

Production: requires JWT token (via Authorization header).
Dev/Test: falls back to X-User-Role header.
"""

from __future__ import annotations

from functools import wraps
from typing import Callable

from fastapi import HTTPException, Request

from config import settings

# Role hierarchy: higher index = more permissions
ROLE_HIERARCHY: dict[str, int] = {
    "viewer": 0,
    "operator": 1,
    "admin": 2,
}

# Permission matrix: action -> minimum role level
# "read" is allowed for all roles (viewer+)
# "write" requires operator+
# "admin" requires admin
PERMISSION_MATRIX: dict[str, str] = {
    # Read operations (viewer+)
    "read:runtime": "viewer",
    "read:run": "viewer",
    "read:workflow": "viewer",
    "read:connector": "viewer",
    "read:eval": "viewer",
    "read:approval": "viewer",
    "read:audit": "viewer",
    "read:environment": "viewer",
    # Write operations (operator+)
    "write:runtime": "operator",
    "write:run": "operator",
    "write:workflow": "operator",
    "write:connector": "operator",
    "write:eval": "operator",
    "write:approval": "operator",
    "write:environment": "operator",
    # Admin operations
    "admin:user": "admin",
    "admin:team": "admin",
    "admin:retention": "admin",
    "admin:environment": "admin",
}


def check_permission(user_role: str, action: str, resource: str) -> bool:
    """Check if a user role has permission for an action on a resource.

    Args:
        user_role: The user's role ("admin", "operator", "viewer").
        action: The action ("read", "write", "admin").
        resource: The resource type ("runtime", "run", "workflow", etc.).

    Returns:
        True if permitted, False otherwise.
    """
    permission_key = f"{action}:{resource}"
    required_role = PERMISSION_MATRIX.get(permission_key)

    if required_role is None:
        # Unknown permission key — deny by default
        return False

    user_level = ROLE_HIERARCHY.get(user_role, -1)
    required_level = ROLE_HIERARCHY.get(required_role, 999)

    return user_level >= required_level


def require_role(required_role: str) -> Callable:
    """FastAPI dependency that checks the current user's role.

    Usage:
        @router.post("/...", dependencies=[Depends(require_role("operator"))])
        def my_endpoint(...):
            ...

    Production: extracts role from JWT token via Authorization header.
    Dev/Test: falls back to X-User-Role header.
    """
    required_level = ROLE_HIERARCHY.get(required_role, 999)

    def dependency(request: Request):
        user_role = _extract_role(request)
        user_level = ROLE_HIERARCHY.get(user_role, -1)
        if user_level < required_level:
            raise HTTPException(
                status_code=403,
                detail=f"Insufficient permissions: requires {required_role}, has {user_role}",
            )
        return user_role

    return dependency


def _extract_role(request: Request) -> str:
    """Extract user role from service token, JWT token, or header.

    Production mode: requires service token or JWT token.
    Dev/Test mode: falls back to X-User-Role header.
    """
    # 1. Service token check
    service_token = request.headers.get("X-Service-Token", "")
    if service_token:
        from security.auth import validate_service_token
        if validate_service_token(service_token):
            return "operator"

    auth_header = request.headers.get("Authorization", "")

    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        # Check if Bearer is a service token
        from security.auth import validate_service_token
        if validate_service_token(token):
            return "operator"
        try:
            import jwt as pyjwt

            payload = pyjwt.decode(
                token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
            )
            return payload.get("role", "viewer")
        except Exception:
            # Invalid token in production = 401
            if settings.environment == "production":
                raise HTTPException(status_code=401, detail="Invalid or expired token")
            # In dev/test, fall through to header check

    # Dev/test fallback: X-User-Role header
    if settings.environment != "production":
        return request.headers.get("X-User-Role", "viewer")

    # Production with no token
    raise HTTPException(status_code=401, detail="Authentication required")
