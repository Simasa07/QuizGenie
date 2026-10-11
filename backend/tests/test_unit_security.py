"""
Unit tests for app/core/security.py - no DB, no HTTP, no network.
Pure functions tested in isolation.
"""
import time
import jwt
import pytest

from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    decode_access_token,
    SECRET_KEY,
    ALGORITHM,
)


class TestPasswordHashing:
    def test_hash_is_not_the_plaintext(self):
        hashed = hash_password("correcthorse123")
        assert hashed != "correcthorse123"

    def test_hash_looks_like_bcrypt(self):
        hashed = hash_password("correcthorse123")
        assert hashed.startswith("$2b$") or hashed.startswith("$2a$")

    def test_correct_password_verifies(self):
        hashed = hash_password("correcthorse123")
        assert verify_password("correcthorse123", hashed) is True

    def test_wrong_password_fails(self):
        hashed = hash_password("correcthorse123")
        assert verify_password("wrongpassword", hashed) is False

    def test_same_password_hashed_twice_gives_different_hashes(self):
        # bcrypt generates a random salt per call - this is what makes
        # rainbow-table attacks against the DB infeasible.
        hash_a = hash_password("samepassword")
        hash_b = hash_password("samepassword")
        assert hash_a != hash_b
        # but both still verify correctly against the same plaintext
        assert verify_password("samepassword", hash_a)
        assert verify_password("samepassword", hash_b)

    def test_verify_against_malformed_hash_does_not_crash(self):
        # e.g. a leftover empty/corrupt value - should fail closed, not throw
        assert verify_password("anything", "") is False
        assert verify_password("anything", "not-a-real-bcrypt-hash") is False

    def test_passwords_longer_than_72_bytes_do_not_crash(self):
        very_long_password = "a" * 200
        hashed = hash_password(very_long_password)
        assert verify_password(very_long_password, hashed) is True


class TestAccessTokens:
    def test_token_round_trips_to_the_same_user_id(self):
        token = create_access_token(user_id=42)
        assert decode_access_token(token) == 42

    def test_tampered_token_is_rejected(self):
        token = create_access_token(user_id=42)
        tampered = token[:-4] + "xxxx"  # corrupt the signature
        assert decode_access_token(tampered) is None

    def test_garbage_token_is_rejected(self):
        assert decode_access_token("not.a.jwt") is None
        assert decode_access_token("") is None

    def test_token_signed_with_a_different_secret_is_rejected(self):
        forged = jwt.encode({"sub": "42", "exp": time.time() + 3600}, "wrong-secret", algorithm=ALGORITHM)
        assert decode_access_token(forged) is None

    def test_expired_token_is_rejected(self):
        expired = jwt.encode(
            {"sub": "42", "exp": time.time() - 10},  # already expired
            SECRET_KEY,
            algorithm=ALGORITHM,
        )
        assert decode_access_token(expired) is None
