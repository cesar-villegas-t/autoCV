"""Account use cases: register, sign in, sign out and resolve a session cookie."""
import re
from datetime import datetime, timedelta, timezone
from typing import Callable, Protocol

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from autocv.infrastructure.db.models import User, UserSession
from autocv.infrastructure.security import Argon2Hasher, hash_token, new_session_token

EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
MIN_PASSWORD_LENGTH = 10
MAX_PASSWORD_LENGTH = 128
MAX_TOKEN_LENGTH = 256


class AuthError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


class Hasher(Protocol):
    def hash(self, password: str) -> str: ...
    def verify(self, password_hash: str, password: str) -> bool: ...
    def needs_rehash(self, password_hash: str) -> bool: ...


def normalize_email(email: str) -> str:
    return email.strip().lower()


class AuthService:
    def __init__(self, hasher: Hasher | None = None, ttl: timedelta = timedelta(days=7),
                 clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc)):
        self.hasher = hasher or Argon2Hasher()
        self.ttl = ttl
        self.clock = clock
        # Verified against when the email is unknown, so timing does not reveal accounts.
        self._decoy_hash = self.hasher.hash("decoy-password-never-used")

    def register(self, db: Session, email: str, password: str) -> tuple[User, str]:
        email = normalize_email(email)
        if len(email) > 320 or not EMAIL_PATTERN.match(email):
            raise AuthError("invalid_email", "Enter a valid email address.")
        if not MIN_PASSWORD_LENGTH <= len(password) <= MAX_PASSWORD_LENGTH:
            raise AuthError("weak_password", f"The password must be {MIN_PASSWORD_LENGTH}-{MAX_PASSWORD_LENGTH} characters long.")
        if db.scalar(select(User.id).where(User.email == email)):
            raise AuthError("email_taken", "An account with this email already exists.")
        user = User(email=email, password_hash=self.hasher.hash(password))
        db.add(user)
        try:
            db.flush()
        except IntegrityError:  # Lost a race against a concurrent registration.
            db.rollback()
            raise AuthError("email_taken", "An account with this email already exists.") from None
        token = self._open_session(db, user)
        db.commit()
        return user, token

    def login(self, db: Session, email: str, password: str) -> tuple[User, str]:
        if len(password) > MAX_PASSWORD_LENGTH:  # Bounds hashing work; no such password can exist.
            raise AuthError("invalid_credentials", "Invalid email or password.")
        user = db.scalar(select(User).where(User.email == normalize_email(email)))
        valid = self.hasher.verify(user.password_hash if user else self._decoy_hash, password)
        if not user or not valid:
            raise AuthError("invalid_credentials", "Invalid email or password.")
        if self.hasher.needs_rehash(user.password_hash):
            user.password_hash = self.hasher.hash(password)
        db.execute(delete(UserSession).where(UserSession.expires_at <= self.clock()))
        token = self._open_session(db, user)
        db.commit()
        return user, token

    def logout(self, db: Session, token: str | None) -> None:
        if token and len(token) <= MAX_TOKEN_LENGTH:
            db.execute(delete(UserSession).where(UserSession.token_hash == hash_token(token)))
            db.commit()

    def user_for_token(self, db: Session, token: str | None) -> User | None:
        if not token or len(token) > MAX_TOKEN_LENGTH:
            return None
        session = db.scalar(select(UserSession).where(UserSession.token_hash == hash_token(token)))
        if session is None:
            return None
        if session.expires_at <= self.clock():
            db.delete(session)
            db.commit()
            return None
        return db.get(User, session.user_id)

    def _open_session(self, db: Session, user: User) -> str:
        token = new_session_token()
        db.add(UserSession(user_id=user.id, token_hash=hash_token(token),
                           expires_at=self.clock() + self.ttl))
        return token
