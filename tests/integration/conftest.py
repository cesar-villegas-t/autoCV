"""PostgreSQL fixtures. Tests skip when no test database is reachable."""
import os
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker

ROOT = Path(__file__).resolve().parents[2]
# Matches docker-compose.yml, which is the documented way to get a test database.
DEFAULT_TEST_URL = "postgresql+psycopg://autocv:autocv@127.0.0.1:55432/autocv_test"


def alembic_config(url: str) -> Config:
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT / "migrations"))
    config.set_main_option("sqlalchemy.url", url.replace("%", "%%"))
    return config


@pytest.fixture(scope="session")
def database_url() -> str:
    url = os.getenv("AUTOCV_TEST_DATABASE_URL", DEFAULT_TEST_URL)
    # The schema is dropped and rebuilt, so never accept a database that is not disposable.
    if not (make_url(url).database or "").endswith("_test"):
        pytest.fail("AUTOCV_TEST_DATABASE_URL must point to a database whose name ends in '_test'.")
    return url


@pytest.fixture(scope="session")
def engine(database_url):
    engine = create_engine(database_url, pool_pre_ping=True)
    try:
        with engine.connect():
            pass
    except OperationalError as exc:
        engine.dispose()
        pytest.skip(f"Test database unavailable (start it with `docker compose up -d db`): {type(exc.orig).__name__}")
    config = alembic_config(database_url)
    command.downgrade(config, "base")
    command.upgrade(config, "head")
    yield engine
    engine.dispose()


@pytest.fixture
def db(engine):
    """A session on a clean schema; rows are truncated after every test."""
    session = sessionmaker(engine, expire_on_commit=False)()
    try:
        yield session
    finally:
        session.close()
        with engine.begin() as connection:
            connection.execute(text("TRUNCATE users, sessions, profiles, generations CASCADE"))


# --- API helpers shared by the authenticated endpoint tests ---------------------------------
from fastapi.testclient import TestClient  # noqa: E402

from apps.api.main import create_app  # noqa: E402
from autocv.application.auth import AuthService  # noqa: E402
from autocv.config import Settings  # noqa: E402
from autocv.infrastructure.security import Argon2Hasher  # noqa: E402

ALLOWED_ORIGIN = "http://localhost:5173"
PASSWORD = "correct horse battery"


@pytest.fixture
def make_app(engine, db, tmp_path):
    """Build the real app on the test database. Cheap Argon2 parameters keep tests fast."""
    def build(generator=None, **settings):
        settings = {"output_dir": tmp_path, "cors_origins": (ALLOWED_ORIGIN,), **settings}
        auth = AuthService(Argon2Hasher(time_cost=1, memory_cost=8, parallelism=1))
        return create_app(Settings(**settings), generator=generator,
                          session_factory=sessionmaker(engine, expire_on_commit=False), auth=auth)
    return build


def sign_up(app, email="ana@example.com") -> TestClient:
    """A client with its own cookie jar, already registered and signed in."""
    client = TestClient(app, raise_server_exceptions=False)
    response = client.post("/api/v1/auth/register", json={"email": email, "password": PASSWORD})
    assert response.status_code == 201, response.text
    return client
