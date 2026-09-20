"""Unit tests for the password and session token helpers (EOS-01 a)."""

import re

import pytest
from argon2 import PasswordHasher

from app.core.security import (
    PASSWORD_MAX_LENGTH,
    PasswordPolicyError,
    generate_session_token,
    hash_password,
    hash_session_token,
    password_needs_rehash,
    session_tokens_match,
    validate_password_policy,
    verify_dummy_password,
    verify_password,
)

pytestmark = pytest.mark.unit

PASSWORD = "correct horse battery staple"


def test_hash_is_argon2id_and_never_contains_the_password() -> None:
    encoded = hash_password(PASSWORD)

    assert encoded.startswith("$argon2id$")
    assert PASSWORD not in encoded


def test_same_password_gives_different_hashes_because_of_the_salt() -> None:
    assert hash_password(PASSWORD) != hash_password(PASSWORD)


def test_verify_accepts_the_password_and_rejects_another() -> None:
    encoded = hash_password(PASSWORD)

    assert verify_password(PASSWORD, encoded) is True
    assert verify_password(PASSWORD + "x", encoded) is False


@pytest.mark.parametrize("damaged", ["", "not-a-hash", "$argon2id$v=19$broken"])
def test_verify_treats_a_damaged_hash_as_no_match(damaged: str) -> None:
    assert verify_password(PASSWORD, damaged) is False


def test_dummy_verification_never_raises() -> None:
    assert verify_dummy_password(PASSWORD) is None


def test_fresh_hash_needs_no_rehash_but_a_weaker_or_unreadable_one_does() -> None:
    weaker = PasswordHasher(time_cost=1, memory_cost=8, parallelism=1).hash(PASSWORD)

    assert password_needs_rehash(hash_password(PASSWORD)) is False
    assert password_needs_rehash(weaker) is True
    assert password_needs_rehash("not-a-hash") is True


def test_policy_accepts_a_long_passphrase_with_spaces() -> None:
    validate_password_policy(PASSWORD, email="owner@example.com")
    validate_password_policy("a" * 12)


@pytest.mark.parametrize(
    ("password", "message"),
    [
        ("short-one", "at least 12"),
        ("a" * (PASSWORD_MAX_LENGTH + 1), "at most 128"),
        (" " * 12, "must not be blank"),
    ],
)
def test_policy_rejects_by_length_or_blank(password: str, message: str) -> None:
    with pytest.raises(PasswordPolicyError, match=message):
        validate_password_policy(password)


def test_policy_rejects_the_email_address_as_password() -> None:
    with pytest.raises(PasswordPolicyError, match="must not be the e-mail"):
        validate_password_policy("Owner@Example.com", email=" owner@example.com ")


def test_session_tokens_are_long_url_safe_and_unique() -> None:
    tokens = {generate_session_token() for _ in range(200)}

    assert len(tokens) == 200
    for token in tokens:
        assert len(token) >= 43
        assert re.fullmatch(r"[A-Za-z0-9_-]+", token)


def test_token_hash_is_sha256_hex_and_stable() -> None:
    token = generate_session_token()
    digest = hash_session_token(token)

    assert re.fullmatch(r"[0-9a-f]{64}", digest)
    assert digest == hash_session_token(token)
    assert token not in digest


def test_token_matching_is_exact() -> None:
    token = generate_session_token()

    assert session_tokens_match(token, hash_session_token(token)) is True
    assert session_tokens_match(token + "x", hash_session_token(token)) is False
    assert session_tokens_match(token, "0" * 64) is False


@pytest.mark.parametrize("missing", [None, ""])
def test_verify_treats_a_missing_hash_as_no_match(missing: str | None) -> None:
    assert verify_password("correct horse battery staple", missing) is False


def test_a_missing_hash_always_needs_a_rehash() -> None:
    assert password_needs_rehash(None) is True
