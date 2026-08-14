"""
Unit tests for auth service.
Run with: pytest tests/unit/test_auth.py -v
"""

import pytest
from auth.service import hash_password, verify_password, create_access_token, decode_token
from utils.exceptions import Unauthorized


def test_password_hashing():
    plain  = "mysecretpassword"
    hashed = hash_password(plain)

    # Hashed should not equal plain
    assert hashed != plain

    # Verify should return True for correct password
    assert verify_password(plain, hashed) is True

    # Verify should return False for wrong password
    assert verify_password("wrongpassword", hashed) is False


def test_token_create_and_decode():
    user_id = "123e4567-e89b-12d3-a456-426614174000"

    token   = create_access_token(user_id)
    assert isinstance(token, str)
    assert len(token) > 0

    # Decoded should give back the same user_id
    decoded = decode_token(token)
    assert decoded == user_id


def test_invalid_token_raises():
    with pytest.raises(Unauthorized):
        decode_token("this.is.not.a.valid.token")


def test_tampered_token_raises():
    token   = create_access_token("some-user-id")
    tampered = token + "tampered"

    with pytest.raises(Unauthorized):
        decode_token(tampered)