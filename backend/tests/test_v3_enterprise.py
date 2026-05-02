"""Tests for v3.0 Enterprise features.

Covers: secret management, webhook verification, RBAC, audit logging,
environment/retention schemas, user/team schemas, retention worker.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Secret Manager
# ---------------------------------------------------------------------------


class TestSecretManager:
    def test_encrypt_decrypt_roundtrip(self):
        from security.secret_manager import encrypt_secret, decrypt_secret

        plaintext = "sk-test-api-key-12345"
        encrypted = encrypt_secret(plaintext)
        assert encrypted != plaintext
        assert decrypt_secret(encrypted) == plaintext

    def test_encrypt_empty_string(self):
        from security.secret_manager import encrypt_secret, decrypt_secret

        encrypted = encrypt_secret("")
        assert decrypt_secret(encrypted) == ""

    def test_mask_secret(self):
        from security.secret_manager import mask_secret

        assert mask_secret("sk-1234567890abcdef") == "sk-1***********cdef"
        assert mask_secret("short") == "*****"
        assert mask_secret("") == ""

    def test_encrypt_config_secrets(self):
        from security.secret_manager import encrypt_config_secrets, decrypt_config_secrets

        config = {
            "api_key": "sk-secret-123",
            "token": "bearer-xyz",
            "safe_field": "visible",
        }
        encrypted = encrypt_config_secrets(config)
        assert encrypted["safe_field"] == "visible"
        assert encrypted["api_key"] != "sk-secret-123"

        decrypted = decrypt_config_secrets(encrypted)
        assert decrypted["api_key"] == "sk-secret-123"
        assert decrypted["token"] == "bearer-xyz"

    def test_mask_config_secrets(self):
        from security.secret_manager import mask_config_secrets

        config = {"api_key": "sk-1234567890", "name": "visible"}
        masked = mask_config_secrets(config)
        assert masked["name"] == "visible"
        assert "*" in masked["api_key"]

    def test_encrypt_config_none(self):
        from security.secret_manager import encrypt_config_secrets

        assert encrypt_config_secrets(None) is None

    def test_decrypt_config_none(self):
        from security.secret_manager import decrypt_config_secrets

        assert decrypt_config_secrets(None) is None


# ---------------------------------------------------------------------------
# Webhook Verification
# ---------------------------------------------------------------------------


class TestWebhookVerification:
    def test_sign_and_verify(self):
        from security.webhook import sign_payload, verify_signature

        payload = b'{"event_type": "run.created"}'
        secret = "webhook-secret-key"
        signature = sign_payload(payload, secret)
        assert signature.startswith("sha256=")
        assert verify_signature(payload, signature, secret)

    def test_verify_wrong_secret(self):
        from security.webhook import sign_payload, verify_signature

        payload = b'{"event_type": "run.created"}'
        signature = sign_payload(payload, "correct-secret")
        with pytest.raises(ValueError):
            verify_signature(payload, signature, "wrong-secret")

    def test_verify_wrong_payload(self):
        from security.webhook import sign_payload, verify_signature

        secret = "webhook-secret-key"
        signature = sign_payload(b"original", secret)
        with pytest.raises(ValueError):
            verify_signature(b"tampered", signature, secret)

    def test_verify_empty_signature(self):
        from security.webhook import verify_signature

        with pytest.raises(ValueError):
            verify_signature(b"data", "", "secret")


# ---------------------------------------------------------------------------
# RBAC
# ---------------------------------------------------------------------------


class TestRBAC:
    def test_check_permission_admin_full_access(self):
        from security.rbac import check_permission

        assert check_permission("admin", "read", "workflow") is True
        assert check_permission("admin", "write", "workflow") is True
        assert check_permission("admin", "admin", "user") is True

    def test_check_permission_operator_read_write(self):
        from security.rbac import check_permission

        assert check_permission("operator", "read", "workflow") is True
        assert check_permission("operator", "write", "workflow") is True

    def test_check_permission_viewer_read_only(self):
        from security.rbac import check_permission

        assert check_permission("viewer", "read", "workflow") is True
        assert check_permission("viewer", "write", "workflow") is False
        assert check_permission("viewer", "delete", "workflow") is False

    def test_role_hierarchy(self):
        from security.rbac import ROLE_HIERARCHY

        assert ROLE_HIERARCHY["viewer"] < ROLE_HIERARCHY["operator"]
        assert ROLE_HIERARCHY["operator"] < ROLE_HIERARCHY["admin"]


# ---------------------------------------------------------------------------
# Audit Logging
# ---------------------------------------------------------------------------


class TestAuditLogging:
    def test_write_audit_log(self):
        from security.audit import write_audit_log

        db = MagicMock()
        log = write_audit_log(
            db,
            actor_type="user",
            actor_id="test-user",
            action="test.action",
            resource_type="test",
            resource_id="res-123",
            before_json={"status": "old"},
            after_json={"status": "new"},
        )

        db.add.assert_called_once()
        db.flush.assert_called_once()
        added_obj = db.add.call_args[0][0]
        assert added_obj.action == "test.action"
        assert added_obj.actor_type == "user"
        assert added_obj.resource_type == "test"


# ---------------------------------------------------------------------------
# Environment Schemas
# ---------------------------------------------------------------------------


class TestEnvironmentSchemas:
    def test_environment_create_schema(self):
        from schemas.environment import EnvironmentCreate

        env = EnvironmentCreate(name="staging", description="Staging env")
        assert env.name == "staging"
        assert env.is_default is False

    def test_environment_response_schema(self):
        from schemas.environment import EnvironmentResponse

        data = {
            "id": uuid.uuid4(),
            "name": "prod",
            "description": "Production",
            "is_default": True,
            "created_at": datetime.now(timezone.utc),
        }
        resp = EnvironmentResponse.model_validate(data)
        assert resp.name == "prod"
        assert resp.is_default is True


# ---------------------------------------------------------------------------
# User/Team Schemas
# ---------------------------------------------------------------------------


class TestUserSchemas:
    def test_user_create_schema(self):
        from schemas.user import UserCreate

        user = UserCreate(email="test@example.com", display_name="Test User")
        assert user.email == "test@example.com"
        assert user.role == "viewer"

    def test_user_create_with_role(self):
        from schemas.user import UserCreate

        user = UserCreate(
            email="admin@example.com",
            display_name="Admin",
            role="admin",
        )
        assert user.role == "admin"

    def test_user_create_invalid_role(self):
        from schemas.user import UserCreate
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            UserCreate(
                email="bad@example.com",
                display_name="Bad",
                role="superadmin",
            )

    def test_team_create_schema(self):
        from schemas.user import TeamCreate

        team = TeamCreate(name="Platform", description="Platform team")
        assert team.name == "Platform"


# ---------------------------------------------------------------------------
# Retention Worker
# ---------------------------------------------------------------------------


class TestRetentionWorker:
    def test_run_retention_cycle_no_policies(self):
        from workers.retention_worker import run_retention_cycle

        with patch("workers.retention_worker.Session") as mock_session_cls:
            mock_session = MagicMock()
            mock_session_cls.return_value = mock_session
            mock_session.query.return_value.filter.return_value.all.return_value = []

            results = run_retention_cycle(dry_run=True)
            assert results == {}
            mock_session.close.assert_called_once()


# ---------------------------------------------------------------------------
# Security Hardening Tests
# ---------------------------------------------------------------------------


class TestSecurityHardening:
    def test_rbac_defaults_to_viewer_when_no_header(self):
        """require_role must deny by default (least privilege)."""
        from security.rbac import require_role
        from fastapi import Request

        dep = require_role("admin")
        mock_request = MagicMock(spec=Request)
        mock_request.headers = {}  # No X-User-Role header

        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            dep(mock_request)
        assert exc_info.value.status_code == 403

    def test_rbac_viewer_cannot_write(self):
        """Viewer role must not pass operator-level checks."""
        from security.rbac import require_role
        from fastapi import Request, HTTPException

        dep = require_role("operator")
        mock_request = MagicMock(spec=Request)
        mock_request.headers = {"X-User-Role": "viewer"}

        with pytest.raises(HTTPException) as exc_info:
            dep(mock_request)
        assert exc_info.value.status_code == 403

    def test_rbac_operator_passes_operator_check(self):
        """Operator role must pass operator-level checks."""
        from security.rbac import require_role
        from fastapi import Request

        dep = require_role("operator")
        mock_request = MagicMock(spec=Request)
        mock_request.headers = {"X-User-Role": "operator"}

        result = dep(mock_request)
        assert result == "operator"

    def test_webhook_anti_replay_rejects_stale_timestamp(self):
        """Webhook with stale timestamp must be rejected."""
        import json
        import time
        from security.webhook import sign_payload, verify_signature

        secret = "test-secret"
        stale_ts = time.time() - 600  # 10 minutes ago
        payload = json.dumps({"timestamp": stale_ts, "event_type": "run.created"}).encode()
        signature = sign_payload(payload, secret)

        with pytest.raises(ValueError, match="stale"):
            verify_signature(payload, signature, secret, tolerance_seconds=300)

    def test_webhook_anti_replay_accepts_fresh_timestamp(self):
        """Webhook with fresh timestamp must pass."""
        import json
        import time
        from security.webhook import sign_payload, verify_signature

        secret = "test-secret"
        fresh_ts = time.time()
        payload = json.dumps({"timestamp": fresh_ts, "event_type": "run.created"}).encode()
        signature = sign_payload(payload, secret)

        assert verify_signature(payload, signature, secret, tolerance_seconds=300) is True

    def test_encryption_key_required_in_production(self):
        """Must raise RuntimeError when ENCRYPTION_KEY is missing in production."""
        import os
        from security.secret_manager import _get_fernet

        # Reset cached Fernet instance
        import security.secret_manager as sm
        sm._fernet = None

        old_key = os.environ.pop("ENCRYPTION_KEY", None)
        old_env = os.environ.pop("ENVIRONMENT", None)
        try:
            os.environ["ENVIRONMENT"] = "production"
            with pytest.raises(RuntimeError, match="ENCRYPTION_KEY must be set"):
                _get_fernet()
        finally:
            if old_key:
                os.environ["ENCRYPTION_KEY"] = old_key
            if old_env:
                os.environ["ENVIRONMENT"] = old_env
            else:
                os.environ.pop("ENVIRONMENT", None)
            sm._fernet = None

    def test_masked_secret_never_in_encrypted_value(self):
        """Masking an encrypted value should still produce masked output."""
        from security.secret_manager import encrypt_secret, mask_secret

        encrypted = encrypt_secret("super-secret-api-key-12345")
        masked = mask_secret(encrypted)
        assert "super-secret" not in masked
        assert "*" in masked

    def test_decrypt_config_secrets_handles_legacy_plaintext(self):
        """Legacy plaintext secrets should pass through without error."""
        from security.secret_manager import decrypt_config_secrets

        legacy_config = {"api_key": "plaintext-key-12345", "name": "my-connector"}
        result = decrypt_config_secrets(legacy_config)
        # Should not raise, should pass through plaintext
        assert result["api_key"] == "plaintext-key-12345"
        assert result["name"] == "my-connector"
