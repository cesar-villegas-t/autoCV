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
