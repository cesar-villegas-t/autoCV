from datetime import datetime, timedelta, timezone

import pytest
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from autocv.infrastructure.db.models import Base, Generation, Profile, User, UserSession
from autocv.infrastructure.db.session import create_db_engine, create_session_factory
from sqlalchemy import inspect, select
from sqlalchemy.exc import IntegrityError


def make_user(email="ana@example.com") -> User:
    return User(email=email, password_hash="hash")


def test_migration_creates_expected_tables(engine):
    assert {"users", "sessions", "profiles", "generations"} <= set(inspect(engine).get_table_names())


def test_models_match_migrations(engine):
    with engine.connect() as connection:
        diff = compare_metadata(MigrationContext.configure(connection), Base.metadata)
    assert diff == []


def test_user_defaults_and_roundtrip(db):
    user = make_user()
    db.add(user)
    db.commit()
    stored = db.scalars(select(User)).one()
    assert stored.id and stored.created_at.tzinfo is not None


def test_email_is_unique(db):
    db.add_all([make_user(), make_user()])
    with pytest.raises(IntegrityError):
        db.commit()


def test_email_must_be_lowercase(db):
    db.add(make_user("Ana@Example.com"))
    with pytest.raises(IntegrityError):
        db.commit()


def test_deleting_user_cascades(db):
    user = make_user()
    db.add(user)
    db.flush()
    db.add_all([
        UserSession(user_id=user.id, token_hash="a" * 64,
                    expires_at=datetime.now(timezone.utc) + timedelta(days=1)),
        Profile(user_id=user.id, data={"name": "Ana"}),
        Generation(id=__import__("uuid").uuid4(), user_id=user.id),
    ])
    db.commit()
    db.delete(user)
    db.commit()
    for model in (UserSession, Profile, Generation):
        assert db.scalars(select(model)).all() == []


def test_session_token_hash_is_unique(db):
    user = make_user()
    db.add(user)
    db.flush()
    expires = datetime.now(timezone.utc) + timedelta(days=1)
    db.add_all([UserSession(user_id=user.id, token_hash="b" * 64, expires_at=expires),
                UserSession(user_id=user.id, token_hash="b" * 64, expires_at=expires)])
    with pytest.raises(IntegrityError):
        db.commit()


def test_profile_data_is_jsonb_roundtrip(db):
    user = make_user()
    db.add(user)
    db.flush()
    data = {"experience": [{"company": "Bdeo", "bullets": ["a", "b"]}]}
    db.add(Profile(user_id=user.id, data=data))
    db.commit()
    db.expire_all()
    assert db.get(Profile, user.id).data == data


def test_engine_requires_configured_url():
    with pytest.raises(ValueError, match="not configured"):
        create_db_engine("")


def test_session_factory_keeps_objects_usable_after_commit(engine):
    with create_session_factory(engine)() as session:
        user = make_user("zoe@example.com")
        session.add(user)
        session.commit()
        assert user.email == "zoe@example.com"
        session.delete(user)
        session.commit()
