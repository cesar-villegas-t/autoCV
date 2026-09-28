import hashlib
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock

import pytest
from apps.api.main import create_app
from apps.api.routes.auth import SESSION_COOKIE
from autocv.application.auth import AuthError, AuthService
from autocv.config import Settings
from autocv.infrastructure.db.models import User, UserSession
from autocv.infrastructure.security import Argon2Hasher
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import sessionmaker

FAST = dict(time_cost=1, memory_cost=8, parallelism=1)  # Test-only; production uses argon2 defaults.
ALLOWED_ORIGIN = "http://localhost:5173"
CREDENTIALS = {"email": "ana@example.com", "password": "correct horse battery"}


class Clock:
    def __init__(self):
        self.now = datetime(2030, 1, 1, tzinfo=timezone.utc)

    def __call__(self):
        return self.now


@pytest.fixture
def clock():
    return Clock()


@pytest.fixture
def hasher():
    return Argon2Hasher(**FAST)


@pytest.fixture
def client(engine, db, tmp_path, clock, hasher):
    settings = Settings(output_dir=tmp_path, cors_origins=(ALLOWED_ORIGIN,))
    auth = AuthService(hasher, ttl=timedelta(days=7), clock=clock)
    app = create_app(settings, session_factory=sessionmaker(engine, expire_on_commit=False), auth=auth)
    with TestClient(app, raise_server_exceptions=False) as client:
        yield client


def register(client, **overrides):
    return client.post("/api/v1/auth/register", json={**CREDENTIALS, **overrides})


def test_register_signs_the_user_in_with_a_hardened_cookie(client):
    response = register(client)
    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "ana@example.com"
    assert set(body) == {"id", "email", "created_at"}
    cookie = response.headers["set-cookie"].lower()
    assert "httponly" in cookie and "samesite=lax" in cookie and "path=/" in cookie
    assert "secure" not in cookie  # Local development over http; enabled via AUTOCV_COOKIE_SECURE.
    assert client.get("/api/v1/auth/me").json()["email"] == "ana@example.com"


def test_secure_flag_follows_configuration(engine, db, tmp_path, hasher):
    settings = Settings(output_dir=tmp_path, cookie_secure=True)
    app = create_app(settings, session_factory=sessionmaker(engine), auth=AuthService(hasher))
    with TestClient(app) as secure_client:
        response = register(secure_client)
    assert "secure" in response.headers["set-cookie"].lower()


def test_password_and_token_are_never_stored_in_clear(client, db):
    register(client)
    user = db.scalars(select(User)).one()
    assert user.password_hash.startswith("$argon2id$")
    assert CREDENTIALS["password"] not in user.password_hash
    token = client.cookies.get(SESSION_COOKIE)
    stored = db.scalars(select(UserSession)).one()
    assert stored.token_hash == hashlib.sha256(token.encode()).hexdigest() != token


def test_email_is_normalized_and_unique_case_insensitively(client, db):
    assert register(client, email="  Ana@Example.COM ").status_code == 201
    assert db.scalars(select(User.email)).one() == "ana@example.com"
    duplicate = register(client, email="ANA@example.com")
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "email_taken"
    assert db.scalar(select(func.count()).select_from(User)) == 1


@pytest.mark.parametrize("overrides,code", [
    ({"email": "not-an-email"}, "invalid_email"),
    ({"email": "a@b"}, "invalid_email"),
    ({"password": "short"}, "weak_password"),
])
def test_invalid_registration_is_rejected_without_echoing_input(client, overrides, code):
    response = register(client, **overrides)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == code
    for value in overrides.values():
        assert value not in response.text
    assert SESSION_COOKIE not in response.cookies


def test_oversized_and_unexpected_fields_are_rejected(client):
    assert register(client, password="x" * 129).status_code == 422
    assert client.post("/api/v1/auth/register", json={**CREDENTIALS, "admin": True}).status_code == 422


def test_login_success_and_uniform_failure(client):
    register(client)
    client.cookies.clear()
    assert client.post("/api/v1/auth/login", json=CREDENTIALS).status_code == 200
    assert client.get("/api/v1/auth/me").status_code == 200

    client.cookies.clear()
    wrong = client.post("/api/v1/auth/login", json={**CREDENTIALS, "password": "wrong password!"})
    unknown = client.post("/api/v1/auth/login", json={"email": "nobody@example.com", "password": "whatever password"})
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json() == unknown.json()
    assert wrong.json()["error"]["code"] == "invalid_credentials"
    assert SESSION_COOKIE not in wrong.cookies


def test_unknown_email_still_performs_a_password_verification(engine, db, clock):
    hasher = Mock(wraps=Argon2Hasher(**FAST))
    service = AuthService(hasher, clock=clock)
    hasher.verify.reset_mock()
    with pytest.raises(AuthError):
        service.login(db, "ghost@example.com", "some password")
    assert hasher.verify.call_count == 1
    # A real Argon2 hash, so the cost (and timing) matches a genuine account.
    assert hasher.verify.call_args.args[0].startswith("$argon2id$")


def test_login_upgrades_outdated_password_hashes(engine, db, clock):
    old = AuthService(Argon2Hasher(**FAST), clock=clock)
    old.register(db, **CREDENTIALS)
    before = db.scalars(select(User.password_hash)).one()
    newer = AuthService(Argon2Hasher(time_cost=2, memory_cost=8, parallelism=1), clock=clock)
    newer.login(db, **CREDENTIALS)
    after = db.scalars(select(User.password_hash)).one()
    assert after != before
    assert newer.hasher.verify(after, CREDENTIALS["password"])


def test_me_requires_a_valid_session(client):
    assert client.get("/api/v1/auth/me").status_code == 401
    client.cookies.set(SESSION_COOKIE, "garbage")
    assert client.get("/api/v1/auth/me").status_code == 401
    client.cookies.set(SESSION_COOKIE, "x" * 5000)
    assert client.get("/api/v1/auth/me").status_code == 401


def test_logout_revokes_the_session_on_the_server(client, db):
    register(client)
    token = client.cookies.get(SESSION_COOKIE)
    response = client.post("/api/v1/auth/logout")
    assert response.status_code == 204
    assert db.scalar(select(func.count()).select_from(UserSession)) == 0
    # A stolen copy of the cookie stops working too.
    client.cookies.set(SESSION_COOKIE, token)
    assert client.get("/api/v1/auth/me").status_code == 401
    assert client.post("/api/v1/auth/logout").status_code == 204  # Idempotent.


def test_sessions_expire(client, db, clock):
    register(client)
    clock.now += timedelta(days=6, hours=23)
    assert client.get("/api/v1/auth/me").status_code == 200
    clock.now += timedelta(hours=2)
    assert client.get("/api/v1/auth/me").status_code == 401
    assert db.scalar(select(func.count()).select_from(UserSession)) == 0


def test_login_purges_expired_sessions(client, db, clock):
    register(client)
    clock.now += timedelta(days=8)
    client.cookies.clear()
    client.post("/api/v1/auth/login", json=CREDENTIALS)
    assert db.scalar(select(func.count()).select_from(UserSession)) == 1


def test_registration_race_is_reported_as_email_taken(engine, db, hasher, clock, monkeypatch):
    service = AuthService(hasher, clock=clock)
    service.register(db, **CREDENTIALS)
    monkeypatch.setattr(db, "scalar", lambda *args, **kwargs: None)  # The pre-check misses the row.
    with pytest.raises(AuthError) as caught:
        service.register(db, **CREDENTIALS)
    assert caught.value.code == "email_taken"
    monkeypatch.undo()
    assert db.scalar(select(func.count()).select_from(User)) == 1  # The session is still usable.


def test_cross_origin_writes_are_rejected_before_reaching_the_handler(client, db):
    hostile = client.post("/api/v1/auth/register", json=CREDENTIALS, headers={"Origin": "https://evil.example"})
    assert hostile.status_code == 403
    assert hostile.json()["error"]["code"] == "forbidden_origin"
    assert db.scalar(select(func.count()).select_from(User)) == 0
    assert client.post("/api/v1/auth/logout", headers={"Origin": "null"}).status_code == 403
    assert register(client, ).status_code == 201  # No Origin (non-browser client) is fine.
    client.cookies.clear()
    assert client.post("/api/v1/auth/login", json=CREDENTIALS, headers={"Origin": ALLOWED_ORIGIN}).status_code == 200
    assert client.post("/api/v1/auth/login", json=CREDENTIALS, headers={"Origin": "http://testserver"}).status_code == 200


def test_cors_allows_credentials_only_for_configured_origins(client):
    allowed = client.options("/api/v1/auth/login", headers={
        "Origin": ALLOWED_ORIGIN, "Access-Control-Request-Method": "POST"})
    assert allowed.headers["access-control-allow-origin"] == ALLOWED_ORIGIN
    assert allowed.headers["access-control-allow-credentials"] == "true"
    denied = client.options("/api/v1/auth/login", headers={
        "Origin": "https://evil.example", "Access-Control-Request-Method": "POST"})
    assert "access-control-allow-origin" not in denied.headers


def test_auth_endpoints_report_missing_database(tmp_path):
    with TestClient(create_app(Settings(output_dir=tmp_path)), raise_server_exceptions=False) as client:
        for response in (client.get("/api/v1/auth/me"), register(client)):
            assert response.status_code == 503
            assert response.json()["error"]["code"] == "not_configured"
        assert client.get("/api/v1/health").status_code == 200
