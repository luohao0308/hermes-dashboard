"""Auth MVP tests for v3.0.

Tests:
- Password hashing and verification
- JWT token creation and decoding
- _extract_role with JWT token
- _extract_role with X-User-Role header (dev mode)
- require_role integration with JWT
"""

from __future__ import annotations

from datetime import timedelta

import pytest
from fastapi import HTTPException

from security.auth import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)
from security.rbac import _extract_role, require_role


# ---------------------------------------------------------------------------
# Password tests
# ---------------------------------------------------------------------------


class TestPasswordHashing:
    def test_hash_and_verify(self):
        hashed = hash_password("secure-password")
        assert verify_password("secure-password", hashed) is True

    def test_wrong_password_fails(self):
        hashed = hash_password("correct-password")
        assert verify_password("wrong-password", hashed) is False

    def test_different_hashes_for_same_input(self):
        h1 = hash_password("same-password")
        h2 = hash_password("same-password")
        assert h1 != h2

    def test_empty_password_can_be_hashed(self):
        hashed = hash_password("")
        assert verify_password("", hashed) is True


# ---------------------------------------------------------------------------
# JWT tests
# ---------------------------------------------------------------------------


class TestJWTToken:
    def test_create_and_decode(self):
        token = create_access_token("user-123", "operator")
        payload = decode_access_token(token)
        assert payload["sub"] == "user-123"
        assert payload["role"] == "operator"
        assert "exp" in payload
        assert "iat" in payload

    def test_custom_expiry(self):
        token = create_access_token("user-1", "viewer", expires_delta=timedelta(seconds=5))
        payload = decode_access_token(token)
        assert payload["sub"] == "user-1"

    def test_expired_token_raises_401(self):
        token = create_access_token("user-1", "viewer", expires_delta=timedelta(seconds=-1))
        with pytest.raises(HTTPException) as exc_info:
            decode_access_token(token)
        assert exc_info.value.status_code == 401

    def test_invalid_token_raises_401(self):
        with pytest.raises(HTTPException) as exc_info:
            decode_access_token("not-a-valid-token")
        assert exc_info.value.status_code == 401

    def test_tampered_token_raises_401(self):
        token = create_access_token("user-1", "admin")
        tampered = token[:-5] + "XXXXX"
        with pytest.raises(HTTPException):
            decode_access_token(tampered)


# ---------------------------------------------------------------------------
# _extract_role tests
# ---------------------------------------------------------------------------


class _FakeRequest:
    def __init__(self, headers: dict | None = None):
        self.headers = headers or {}


class TestExtractRole:
    def test_jwt_token_in_dev_mode(self):
        token = create_access_token("u1", "operator")
        req = _FakeRequest({"Authorization": f"Bearer {token}"})
        role = _extract_role(req)
        assert role == "operator"

    def test_header_fallback_in_dev_mode(self):
        req = _FakeRequest({"X-User-Role": "admin"})
        role = _extract_role(req)
        assert role == "admin"

    def test_no_auth_defaults_to_viewer_in_dev(self):
        req = _FakeRequest({})
        role = _extract_role(req)
        assert role == "viewer"

    def test_invalid_token_in_dev_falls_back_to_header(self):
        req = _FakeRequest({
            "Authorization": "Bearer invalid-token",
            "X-User-Role": "operator",
        })
        role = _extract_role(req)
        assert role == "operator"


# ---------------------------------------------------------------------------
# require_role integration with JWT
# ---------------------------------------------------------------------------


class TestRequireRoleWithJWT:
    def test_jwt_operator_passes_operator_check(self):
        token = create_access_token("u1", "operator")
        dep = require_role("operator")
        req = _FakeRequest({"Authorization": f"Bearer {token}"})
        assert dep(req) == "operator"

    def test_jwt_viewer_blocked_from_operator(self):
        token = create_access_token("u1", "viewer")
        dep = require_role("operator")
        req = _FakeRequest({"Authorization": f"Bearer {token}"})
        with pytest.raises(HTTPException) as exc_info:
            dep(req)
        assert exc_info.value.status_code == 403

    def test_header_still_works_in_dev_mode(self):
        dep = require_role("operator")
        req = _FakeRequest({"X-User-Role": "admin"})
        assert dep(req) == "admin"

    def test_header_viewer_blocked_in_dev(self):
        dep = require_role("operator")
        req = _FakeRequest({"X-User-Role": "viewer"})
        with pytest.raises(HTTPException) as exc_info:
            dep(req)
        assert exc_info.value.status_code == 403
