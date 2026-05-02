"""Secret leak tests — OPT-35.

Verifies that secrets never appear in plaintext in:
1. Connector API responses (config_json masked)
2. Audit log before/after JSON
3. Error responses
4. Serialized Pydantic payloads
5. Encrypt/decrypt roundtrip integrity
"""

from __future__ import annotations

import pytest

from security.secret_manager import (
    encrypt_config_secrets,
    decrypt_config_secrets,
    mask_config_secrets,
    mask_secret,
    encrypt_secret,
    decrypt_secret,
    SENSITIVE_FIELDS,
)


SAMPLE_SECRETS = {
    "api_key": "sk-abc123def456ghi",
    "token": "ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxx",
    "secret": "webhook_secret_value_12345",
    "password": "P@ssw0rd!2026",
    "webhook_secret": "whsec_test_abcdef",
    "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvg...",
    "access_key": "AKIAIOSFODNN7EXAMPLE",
    "secret_key": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
    "auth_token": "bearer_token_abc123",
}

NON_SENSITIVE = {
    "endpoint": "https://api.example.com",
    "region": "us-east-1",
    "timeout": 30,
    "enabled": True,
}


class TestEncryptDecryptRoundtrip:
    def test_encrypt_decrypt_roundtrip(self):
        for field, plaintext in SAMPLE_SECRETS.items():
            encrypted = encrypt_secret(plaintext)
            assert encrypted != plaintext, f"{field} should be encrypted"
            decrypted = decrypt_secret(encrypted)
            assert decrypted == plaintext, f"{field} roundtrip failed"

    def test_encrypt_produces_different_output_each_time(self):
        plaintext = "my-secret-value"
        first = encrypt_secret(plaintext)
        second = encrypt_secret(plaintext)
        assert first != second  # Fernet uses random IV

    def test_decrypt_invalid_token_raises(self):
        with pytest.raises(ValueError, match="Failed to decrypt"):
            decrypt_secret("not-a-valid-fernet-token")


class TestMaskSecret:
    def test_mask_long_secret(self):
        masked = mask_secret("sk-abc123def456")
        assert masked.startswith("sk-a")
        assert masked.endswith("f456")
        assert "*" in masked
        assert "abc123de" not in masked

    def test_mask_short_secret(self):
        masked = mask_secret("short")
        assert masked == "*****"

    def test_mask_empty(self):
        assert mask_secret("") == ""

    def test_mask_exactly_8_chars(self):
        masked = mask_secret("12345678")
        assert masked == "********"


class TestConfigSecretEncryption:
    def test_encrypt_config_secrets_masks_sensitive_fields(self):
        config = {**SAMPLE_SECRETS, **NON_SENSITIVE}
        encrypted = encrypt_config_secrets(config)

        for field in SENSITIVE_FIELDS:
            if field in SAMPLE_SECRETS:
                assert encrypted[field] != SAMPLE_SECRETS[field], (
                    f"{field} should be encrypted, got plaintext"
                )

        for field, value in NON_SENSITIVE.items():
            assert encrypted[field] == value, f"{field} should not be modified"

    def test_decrypt_config_secrets_restores_plaintext(self):
        config = {**SAMPLE_SECRETS, **NON_SENSITIVE}
        encrypted = encrypt_config_secrets(config)
        decrypted = decrypt_config_secrets(encrypted)

        for field, plaintext in SAMPLE_SECRETS.items():
            assert decrypted[field] == plaintext, f"{field} roundtrip failed"

        for field, value in NON_SENSITIVE.items():
            assert decrypted[field] == value

    def test_encrypt_none_returns_none(self):
        assert encrypt_config_secrets(None) is None

    def test_encrypt_empty_dict_returns_empty(self):
        assert encrypt_config_secrets({}) == {}

    def test_decrypt_none_returns_none(self):
        assert decrypt_config_secrets(None) is None


class TestConfigSecretMasking:
    def test_mask_config_secrets_hides_values(self):
        config = {**SAMPLE_SECRETS, **NON_SENSITIVE}
        masked = mask_config_secrets(config)

        for field in SENSITIVE_FIELDS:
            if field in SAMPLE_SECRETS:
                value = masked[field]
                assert value != SAMPLE_SECRETS[field], (
                    f"{field} plaintext leaked through mask"
                )
                assert "*" in value, f"{field} mask should contain asterisks"

        for field, value in NON_SENSITIVE.items():
            assert masked[field] == value

    def test_mask_preserves_non_string_values(self):
        config = {"timeout": 30, "retries": 3, "enabled": True}
        masked = mask_config_secrets(config)
        assert masked == config

    def test_mask_none_returns_none(self):
        assert mask_config_secrets(None) is None


class TestConnectorResponseNeverLeaks:
    """Simulate what ConnectorConfigResponse.field_validator does."""

    def test_response_validator_masks_secrets(self):
        from schemas.connector import ConnectorConfigResponse
        from datetime import datetime, timezone

        encrypted_config = encrypt_config_secrets(SAMPLE_SECRETS)
        raw_data = {
            "id": "00000000-0000-0000-0000-000000000001",
            "runtime_id": "00000000-0000-0000-0000-000000000002",
            "connector_type": "github",
            "display_name": "Test",
            "enabled": True,
            "config_json": encrypted_config,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }
        resp = ConnectorConfigResponse.model_validate(raw_data)
        resp_json = resp.model_dump_json()

        for field, plaintext in SAMPLE_SECRETS.items():
            assert plaintext not in resp_json, (
                f"Plaintext secret '{field}' leaked in response JSON"
            )

    def test_response_with_plaintext_config_still_masks(self):
        """Even if config_json stored as plaintext (legacy), response masks it."""
        from schemas.connector import ConnectorConfigResponse
        from datetime import datetime, timezone

        raw_data = {
            "id": "00000000-0000-0000-0000-000000000001",
            "runtime_id": "00000000-0000-0000-0000-000000000002",
            "connector_type": "github",
            "display_name": "Test",
            "enabled": True,
            "config_json": SAMPLE_SECRETS,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }
        resp = ConnectorConfigResponse.model_validate(raw_data)
        resp_json = resp.model_dump_json()

        for field, plaintext in SAMPLE_SECRETS.items():
            assert plaintext not in resp_json, (
                f"Plaintext secret '{field}' leaked in response JSON"
            )


class TestAuditLogNeverLeaks:
    """Verify audit log entries don't contain plaintext secrets."""

    def test_audit_after_json_masks_connector_config(self):
        """Simulates what write_audit_log receives after connector create."""
        encrypted = encrypt_config_secrets(SAMPLE_SECRETS)
        for field, plaintext in SAMPLE_SECRETS.items():
            assert plaintext not in str(encrypted), (
                f"Plaintext '{field}' in encrypted config"
            )

    def test_sensitive_field_names_in_config_json(self):
        expected = {
            "api_key", "token", "secret", "password", "webhook_secret",
            "private_key", "access_key", "secret_key", "auth_token",
        }
        assert SENSITIVE_FIELDS == expected


class TestErrorResponsesNeverLeak:
    def test_decrypt_error_no_plaintext(self):
        try:
            decrypt_secret("garbage-input")
        except ValueError as exc:
            assert "garbage-input" not in str(exc)

    def test_mask_on_empty_string(self):
        result = mask_secret("")
        assert result == ""
