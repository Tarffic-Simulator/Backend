"""Tests for the encrypted JSON payload helpers."""

from app.core.crypto import encrypt_json_payload, decrypt_json_payload


def test_encrypt_json_payload_roundtrip():
    payload = {"ok": True, "nested": {"value": 3}, "items": [1, 2, 3]}

    encrypted = encrypt_json_payload(payload)

    assert encrypted != '{"ok": true, "nested": {"value": 3}, "items": [1, 2, 3]}'
    assert decrypt_json_payload(encrypted) == payload
