"""Cryptographic helpers for database payload encryption."""

from __future__ import annotations

import base64
import hashlib
import json
from typing import Any

from cryptography.fernet import Fernet

from app.core.config import settings


def _derive_fernet_key() -> bytes:
    """Derive a stable Fernet key from the application secret key."""
    source_key = settings.data_encryption_key or settings.secret_key
    digest = hashlib.sha256(source_key.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest)


_fernet = Fernet(_derive_fernet_key())


def encrypt_json_payload(value: Any) -> str:
    """Serialize and encrypt a JSON-serializable payload."""
    serialized = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    return _fernet.encrypt(serialized.encode("utf-8")).decode("utf-8")


def decrypt_json_payload(value: str) -> Any:
    """Decrypt and deserialize a previously encrypted payload."""
    decrypted = _fernet.decrypt(value.encode("utf-8")).decode("utf-8")
    return json.loads(decrypted)