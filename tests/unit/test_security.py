"""Unit tests: JWT and password hashing."""
from __future__ import annotations

import pytest
from jose import JWTError

from app.core.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    verify_access_token,
    verify_password,
)


def test_hash_and_verify():
    plain = "MySecureP@ss1"
    hashed = hash_password(plain)
    assert hashed != plain
    assert verify_password(plain, hashed)
    assert not verify_password("wrong", hashed)


def test_access_token_roundtrip():
    token = create_access_token("user-123", {"trust_id": "t-1"})
    payload = verify_access_token(token)
    assert payload["sub"] == "user-123"
    assert payload["trust_id"] == "t-1"
    assert payload["type"] == "access"


def test_refresh_token_rejected_as_access():
    token = create_refresh_token("user-123")
    with pytest.raises(JWTError):
        verify_access_token(token)


def test_tampered_token_rejected():
    token = create_access_token("user-123")
    tampered = token[:-5] + "XXXXX"
    with pytest.raises(JWTError):
        verify_access_token(tampered)
