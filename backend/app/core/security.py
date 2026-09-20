"""
Password hashing and session token helpers (EOS-01 a, identity and access).

Passwords are hashed with argon2id through argon2-cffi, using the library defaults. Only the
encoded hash is stored: it carries its own parameters and a random salt, so two users with the
same password get different hashes.

Session tokens are 32 random bytes as URL-safe text. The browser cookie holds the token; the
database stores only its SHA-256, so a copy of the database does not open any session. A fast
hash is enough there because the token is random, not chosen by a person.
"""

import hashlib
import hmac
import secrets

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

PASSWORD_MIN_LENGTH = 12
PASSWORD_MAX_LENGTH = 128
SESSION_TOKEN_BYTES = 32

_hasher = PasswordHasher()

# Hash of a random password nobody knows: verify_dummy_password() spends the same time on an
# unknown e-mail as verify_password() spends on a wrong password.
_DUMMY_HASH = _hasher.hash(secrets.token_urlsafe(32))


class PasswordPolicyError(ValueError):
    """The password does not meet the policy; the message is safe to show to the user."""


def validate_password_policy(password: str, *, email: str | None = None) -> None:
    """Length is what counts: no composition rules, passphrases with spaces are welcome."""

    if len(password) < PASSWORD_MIN_LENGTH:
        raise PasswordPolicyError(f"Password must have at least {PASSWORD_MIN_LENGTH} characters.")
    if len(password) > PASSWORD_MAX_LENGTH:
        raise PasswordPolicyError(f"Password must have at most {PASSWORD_MAX_LENGTH} characters.")
    if not password.strip():
        raise PasswordPolicyError("Password must not be blank.")
    if email is not None and password.casefold() == email.strip().casefold():
        raise PasswordPolicyError("Password must not be the e-mail address.")


def hash_password(password: str) -> str:
    """Return the encoded argon2id hash; the password itself is never stored or logged."""

    return _hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """True only for the matching password; a damaged or foreign hash counts as no match."""

    try:
        return _hasher.verify(password_hash, password)
    except (VerificationError, InvalidHashError):
        return False


def verify_dummy_password(password: str) -> None:
    """Spend one verification when the e-mail is unknown, so timing does not reveal accounts."""

    verify_password(password, _DUMMY_HASH)


def password_needs_rehash(password_hash: str) -> bool:
    """True when the hash was made with weaker parameters than today's, or cannot be read."""

    try:
        return _hasher.check_needs_rehash(password_hash)
    except InvalidHashError:
        return True


def generate_session_token() -> str:
    """A new random session token for the cookie."""

    return secrets.token_urlsafe(SESSION_TOKEN_BYTES)


def hash_session_token(token: str) -> str:
    """SHA-256 of the token as 64 hex characters: the only form kept in the database."""

    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def session_tokens_match(token: str, token_hash: str) -> bool:
    """Constant-time comparison of a presented token with a stored hash."""

    return hmac.compare_digest(hash_session_token(token), token_hash)


__all__ = [
    "PASSWORD_MAX_LENGTH",
    "PASSWORD_MIN_LENGTH",
    "SESSION_TOKEN_BYTES",
    "PasswordPolicyError",
    "generate_session_token",
    "hash_password",
    "hash_session_token",
    "password_needs_rehash",
    "session_tokens_match",
    "validate_password_policy",
    "verify_dummy_password",
    "verify_password",
]
