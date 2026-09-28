"""Password hashing (Argon2id) and session-token helpers."""
import hashlib
import secrets

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError


class Argon2Hasher:
    """Thin wrapper so the application layer depends on behavior, not on argon2."""

    def __init__(self, **parameters):
        self._hasher = PasswordHasher(**parameters)

    def hash(self, password: str) -> str:
        return self._hasher.hash(password)

    def verify(self, password_hash: str, password: str) -> bool:
        try:
            return self._hasher.verify(password_hash, password)
        except (VerificationError, InvalidHashError):
            return False

    def needs_rehash(self, password_hash: str) -> bool:
        return self._hasher.check_needs_rehash(password_hash)


def new_session_token() -> str:
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    """The database only ever stores this digest, never the cookie value."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
