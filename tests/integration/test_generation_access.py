"""Generation and download are private to the signed-in user, and can use the saved profile."""
import json
from unittest.mock import Mock

import pytest
from autocv.application.generation import Generator
from autocv.config import Settings
from autocv.infrastructure.db.models import Generation
from sqlalchemy import select
from tests.fixtures.resume import sample_resume
from tests.integration.conftest import sign_up

OFFER = {"offer_text": "Job requirements", "output_name": "cv.pdf"}
PROFILE = {
    "first_name": "Ana", "last_name": "Ruiz", "email": "ana@example.com", "location": "Madrid, Spain",
    "experience": [{"company": "Bdeo", "title": "Growth Lead", "start_date": "2024-10", "current": True,
                    "description": "Cut churn by 12%\nRan A/B tests"}],
}


@pytest.fixture
def world(engine, tmp_path, make_app):
    settings = Settings(api_key="test-only", output_dir=tmp_path)

    def compile_pdf(tex, name, destination):
        destination.mkdir(parents=True, exist_ok=True)
        pdf = destination / name
        pdf.write_bytes(b"%PDF-1.4\nmock")
        return pdf

    llm = Mock(return_value=json.dumps(sample_resume()))
    generator = Generator(settings, llm=llm, compiler=Mock(side_effect=compile_pdf))
    app = make_app(generator=generator, api_key="test-only")
    return app, llm


def generate(client, **body):
    return client.post("/api/v1/cv/generations", json={**OFFER, **body})


def test_generation_and_download_require_a_session(world):
    app, llm = world
    from fastapi.testclient import TestClient
    anonymous = TestClient(app, raise_server_exceptions=False)
    assert generate(anonymous, profile_text="Facts").status_code == 401
    assert anonymous.get("/api/v1/cv/generations/00000000-0000-0000-0000-000000000000/pdf").status_code == 401
    llm.assert_not_called()


def test_generation_records_its_owner(world, db):
    app, _ = world
    ana = sign_up(app)
    generation_id = generate(ana, profile_text="Facts").json()["id"]
    record = db.scalars(select(Generation)).one()
    assert str(record.id) == generation_id
    assert record.user_id is not None


def test_pdfs_are_only_downloadable_by_their_owner(world):
    app, _ = world
    ana, bea = sign_up(app, "ana@example.com"), sign_up(app, "bea@example.com")
    url = generate(ana, profile_text="Facts").json()["download_url"]
    assert ana.get(url).status_code == 200
    stolen = bea.get(url)
    assert stolen.status_code == 404  # Same answer as a PDF that does not exist.
    assert stolen.json() == ana.get("/api/v1/cv/generations/00000000-0000-0000-0000-000000000000/pdf").json()


def test_failed_generations_are_not_recorded(world, db):
    app, llm = world
    ana = sign_up(app)
    llm.side_effect = RuntimeError("boom")
    assert generate(ana, profile_text="Facts").status_code == 502
    assert db.scalars(select(Generation)).all() == []


def test_no_database_connection_is_held_while_generating(world, engine):
    app, llm = world
    ana = sign_up(app)
    seen = []
    llm.side_effect = lambda *args: (seen.append(engine.pool.checkedout()), json.dumps(sample_resume()))[1]
    assert generate(ana, profile_text="Facts").status_code == 201
    assert seen == [0]


def test_saved_profile_feeds_the_generator(world):
    app, llm = world
    ana = sign_up(app)
    assert ana.put("/api/v1/profile", json=PROFILE).status_code == 200
    assert generate(ana, use_saved_profile=True).status_code == 201
    prompt = llm.call_args.args[1]
    assert "# Ana Ruiz" in prompt and "### Growth Lead | Bdeo" in prompt
    assert "**Dates:** Oct 2024 – Present" in prompt and "- Cut churn by 12%" in prompt


def test_incomplete_saved_profile_is_rejected_before_calling_the_provider(world):
    app, llm = world
    ana = sign_up(app)
    response = generate(ana, use_saved_profile=True)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "profile_incomplete"
    assert "first name" in response.json()["error"]["message"]
    llm.assert_not_called()


def test_users_never_generate_from_someone_elses_profile(world):
    app, llm = world
    ana, bea = sign_up(app, "ana@example.com"), sign_up(app, "bea@example.com")
    ana.put("/api/v1/profile", json=PROFILE)
    assert generate(bea, use_saved_profile=True).status_code == 422  # Bea has an empty profile.
    llm.assert_not_called()


@pytest.mark.parametrize("body", [
    {}, {"profile_text": "Facts", "use_saved_profile": True}, {"use_saved_profile": False},
])
def test_exactly_one_profile_source_is_required(world, body):
    app, llm = world
    assert generate(sign_up(app), **body).status_code == 422
    llm.assert_not_called()
