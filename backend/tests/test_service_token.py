"""Service Token tests for v3.0.

Tests:
- Service token validation
- Service token in get_current_user
- Service token in _extract_role
- Service token via Authorization Bearer
- Service token via X-Service-Token header
"""

from __future__ import annotations

import pytest
from fastapi import HTTPException

from security.auth import get_current_user, validate_service_token
from security.rbac import _extract_role


class _FakeRequest:
    def __init__(self, headers: dict | None = None):
        self.headers = headers or {}


class TestServiceTokenValidation:
    def test_valid_token(self):
        assert validate_service_token("test-token-abc") is True

    def test_valid_second_token(self):
        assert validate_service_token("test-token-xyz") is True

    def test_invalid_token(self):
        assert validate_service_token("wrong-token") is False

    def test_empty_token(self):
        assert validate_service_token("") is False


class TestServiceTokenInExtractRole:
    def test_service_token_gives_operator_role(self):
        req = _FakeRequest({"X-Service-Token": "test-token-abc"})
        role = _extract_role(req)
        assert role == "operator"

    def test_service_token_bearer_gives_operator_role(self):
        req = _FakeRequest({"Authorization": "Bearer test-token-abc"})
        role = _extract_role(req)
        assert role == "operator"

    def test_invalid_service_token_falls_through(self):
        req = _FakeRequest({"X-Service-Token": "invalid", "X-User-Role": "viewer"})
        role = _extract_role(req)
        assert role == "viewer"


class TestServiceTokenInGetCurrentUser:
    def test_service_token_returns_service_user(self):
        req = _FakeRequest({"X-Service-Token": "test-token-abc"})
        user = get_current_user(req, db=None)
        assert user["user_id"] == "service"
        assert user["role"] == "operator"

    def test_service_token_bearer_returns_service_user(self):
        req = _FakeRequest({"Authorization": "Bearer test-token-abc"})
        user = get_current_user(req, db=None)
        assert user["user_id"] == "service"
        assert user["role"] == "operator"

    def test_invalid_service_token_raises_401_in_production(self):
        from config import settings
        original = settings.environment
        try:
            settings.environment = "production"
            req = _FakeRequest({"X-Service-Token": "invalid"})
            with pytest.raises(HTTPException) as exc_info:
                get_current_user(req, db=None)
            assert exc_info.value.status_code == 401
        finally:
            settings.environment = original
