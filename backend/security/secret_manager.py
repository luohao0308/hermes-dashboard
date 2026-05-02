"""Secret management with Fernet symmetric encryption.

Encrypts sensitive fields in connector config_json before storage.
Decrypts on read for authorized users. Masks for viewers.
"""

from __future__ import annotations

import logging
import os

from cryptography.fernet import Fernet, InvalidToken

logger = logging.getLogger(__name__)

# Fields that contain secrets and should be encrypted/masked
SENSITIVE_FIELDS = frozenset({
    "api_key", "token", "secret", "password", "webhook_secret",
    "private_key", "access_key", "secret_key", "auth_token",
})

# Cache the Fernet instance to avoid re-creating on every call
_fernet: Fernet | None = None


def _get_fernet() -> Fernet:
    """Get or create a Fernet instance from ENCRYPTION_KEY env var."""
    global _fernet
    if _fernet is not None:
        return _fernet

    key = os.environ.get("ENCRYPTION_KEY", "").strip()
    if not key:
        environment = os.environ.get("ENVIRONMENT", "development").lower()
        if environment == "production":
            raise RuntimeError(
                "ENCRYPTION_KEY must be set in production. "
                "Generate one with: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
            )
        # Auto-generate a key for development; warn prominently
        key = Fernet.generate_key().decode()
        logger.warning(
            "ENCRYPTION_KEY not set — auto-generated ephemeral key. "
            "Encrypted secrets will be unreadable after restart. "
            "Set ENCRYPTION_KEY in .env for persistent encryption."
        )
        os.environ["ENCRYPTION_KEY"] = key

    _fernet = Fernet(key.encode() if isinstance(key, str) else key)
    return _fernet


def encrypt_secret(plaintext: str) -> str:
    """Encrypt a plaintext string. Returns Fernet token as string."""
    f = _get_fernet()
    return f.encrypt(plaintext.encode("utf-8")).decode("utf-8")


def decrypt_secret(token: str) -> str:
    """Decrypt a Fernet token back to plaintext. Raises ValueError on failure."""
    f = _get_fernet()
    try:
        return f.decrypt(token.encode("utf-8")).decode("utf-8")
    except InvalidToken as exc:
        raise ValueError("Failed to decrypt secret — invalid key or corrupted data") from exc


def mask_secret(value: str) -> str:
    """Mask a secret value: show first 4 and last 4 chars, mask the rest.

    Examples:
        mask_secret("sk-abc123def456") -> "sk-a******f456"
        mask_secret("short") -> "*****"
        mask_secret("") -> ""
    """
    if not value:
        return ""
    if len(value) <= 8:
        return "*" * len(value)
    return value[:4] + "*" * (len(value) - 8) + value[-4:]


def encrypt_config_secrets(config_json: dict | None) -> dict | None:
    """Encrypt sensitive fields in a connector config dict."""
    if not config_json:
        return config_json
    result = {}
    for key, value in config_json.items():
        if key in SENSITIVE_FIELDS and isinstance(value, str) and value:
            result[key] = encrypt_secret(value)
        else:
            result[key] = value
    return result


def decrypt_config_secrets(config_json: dict | None) -> dict | None:
    """Decrypt sensitive fields in a connector config dict."""
    if not config_json:
        return config_json
    result = {}
    for key, value in config_json.items():
        if key in SENSITIVE_FIELDS and isinstance(value, str) and value:
            try:
                result[key] = decrypt_secret(value)
            except ValueError:
                # Not encrypted (legacy plaintext) — pass through
                result[key] = value
        else:
            result[key] = value
    return result


def mask_config_secrets(config_json: dict | None) -> dict | None:
    """Mask sensitive fields in a connector config dict for display."""
    if not config_json:
        return config_json
    result = {}
    for key, value in config_json.items():
        if key in SENSITIVE_FIELDS and isinstance(value, str) and value:
            result[key] = mask_secret(value)
        else:
            result[key] = value
    return result
