"""RBAC coverage tests for v3.0 write API protection.

Tests that:
- viewer cannot perform write operations
- operator can perform allowed write operations
- admin can perform all operations
- unknown roles are denied
"""

from __future__ import annotations

import pytest
from fastapi import HTTPException

from security.rbac import check_permission, require_role, ROLE_HIERARCHY


# ---------------------------------------------------------------------------
# Unit tests: check_permission
# ---------------------------------------------------------------------------


class TestCheckPermission:
    def test_viewer_can_read(self):
        assert check_permission("viewer", "read", "run") is True

    def test_viewer_cannot_write(self):
        assert check_permission("viewer", "write", "run") is False

    def test_viewer_cannot_admin(self):
        assert check_permission("viewer", "admin", "user") is False

    def test_operator_can_read(self):
        assert check_permission("operator", "read", "run") is True

    def test_operator_can_write(self):
        assert check_permission("operator", "write", "run") is True

    def test_operator_cannot_admin(self):
        assert check_permission("operator", "admin", "user") is False

    def test_admin_can_read(self):
        assert check_permission("admin", "read", "run") is True

    def test_admin_can_write(self):
        assert check_permission("admin", "write", "run") is True

    def test_admin_can_admin(self):
        assert check_permission("admin", "admin", "user") is True

    def test_unknown_role_denied(self):
        assert check_permission("unknown", "read", "run") is False

    def test_unknown_permission_denied(self):
        assert check_permission("admin", "unknown", "resource") is False


# ---------------------------------------------------------------------------
# Unit tests: require_role dependency
# ---------------------------------------------------------------------------


class _FakeRequest:
    def __init__(self, headers: dict | None = None):
        self.headers = headers or {}


class TestRequireRole:
    def test_operator_passes_operator_check(self):
        dep = require_role("operator")
        req = _FakeRequest({"X-User-Role": "operator"})
        assert dep(req) == "operator"

    def test_admin_passes_operator_check(self):
        dep = require_role("operator")
        req = _FakeRequest({"X-User-Role": "admin"})
        assert dep(req) == "admin"

    def test_viewer_blocked_from_operator(self):
        dep = require_role("operator")
        req = _FakeRequest({"X-User-Role": "viewer"})
        with pytest.raises(HTTPException) as exc_info:
            dep(req)
        assert exc_info.value.status_code == 403

    def test_operator_blocked_from_admin(self):
        dep = require_role("admin")
        req = _FakeRequest({"X-User-Role": "operator"})
        with pytest.raises(HTTPException) as exc_info:
            dep(req)
        assert exc_info.value.status_code == 403

    def test_no_header_defaults_to_viewer(self):
        dep = require_role("operator")
        req = _FakeRequest({})
        with pytest.raises(HTTPException) as exc_info:
            dep(req)
        assert exc_info.value.status_code == 403

    def test_viewer_defaults_when_no_header(self):
        dep = require_role("admin")
        req = _FakeRequest({})
        with pytest.raises(HTTPException) as exc_info:
            dep(req)
        assert exc_info.value.status_code == 403


# ---------------------------------------------------------------------------
# Unit tests: role hierarchy
# ---------------------------------------------------------------------------


class TestRoleHierarchy:
    def test_viewer_is_lowest(self):
        assert ROLE_HIERARCHY["viewer"] < ROLE_HIERARCHY["operator"]

    def test_operator_is_middle(self):
        assert ROLE_HIERARCHY["operator"] < ROLE_HIERARCHY["admin"]

    def test_admin_is_highest(self):
        assert ROLE_HIERARCHY["admin"] == max(ROLE_HIERARCHY.values())
