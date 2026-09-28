from datetime import datetime

import pytest
from autocv.infrastructure.db.models import Profile, User
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from tests.integration.conftest import sign_up

FULL = {
    "first_name": "Lucía", "last_name": "Morales", "location": "Madrid, Spain",
    "relocations": ["Barcelona", "London"], "phone": "+34 611 458 923", "email": "lucia@example.com",
    "linkedin": "https://linkedin.com/in/lucia", "links": [{"label": "Portfolio", "url": "https://lucia.work"}],
    "summary": "Growth marketer focused on retention.",
    "experience": [
        {"company": "Bdeo", "title": "Growth Specialist", "start_date": "2024-10", "current": True,
         "description": "Redesigned onboarding flows\nManaged EUR 15k monthly budget"},
        {"company": "Cobee", "title": "Intern", "start_date": "2022-06", "end_date": "2022-12"},
    ],
    "education": [{"institution": "UC3M", "degree": "B.Sc. Business", "location": "Madrid",
                   "start_date": "2018-09", "end_date": "2023-06", "grade": "8.1 / 10"}],
    "achievements": [{"name": "Best newcomer 2023", "start_date": "2023-05"}],
    "projects": [{"name": "Churn model", "start_date": "2023-01", "end_date": "2023-03",
                  "description": "Predicted churn in Python"}],
    "skills": "GA4, SQL, HubSpot",
    "languages": [{"language": "English", "level": "C1", "certification": "TOEFL 104"}, {"language": "Spanish"}],
}


@pytest.fixture
def app(make_app):
    return make_app()


@pytest.fixture
def ana(app):
    return sign_up(app)


def test_every_profile_route_requires_a_session(app):
    anonymous = TestClient(app, raise_server_exceptions=False)
    assert anonymous.get("/api/v1/profile").status_code == 401
    assert anonymous.put("/api/v1/profile", json=FULL).status_code == 401
    assert anonymous.delete("/api/v1/profile").status_code == 401
    assert anonymous.get("/api/v1/profile/markdown").status_code == 401


def test_new_users_start_with_an_empty_incomplete_profile(ana):
    body = ana.get("/api/v1/profile").json()
    assert body["updated_at"] is None
    assert body["complete"] is False
    assert body["missing"] == ["name", "email", "experience_or_education"]
    assert body["profile"]["experience"] == [] and body["profile"]["first_name"] == ""


def test_profile_round_trips_and_reports_completeness(ana):
    saved = ana.put("/api/v1/profile", json=FULL)
    assert saved.status_code == 200
    assert saved.json()["complete"] is True and saved.json()["missing"] == []
    assert datetime.fromisoformat(saved.json()["updated_at"])
    read = ana.get("/api/v1/profile").json()
    assert read["profile"]["experience"][0]["current"] is True
    assert read["profile"]["experience"][1]["end_date"] == "2022-12"
    assert read["profile"]["languages"][1] == {"language": "Spanish", "level": "", "certification": ""}
    assert read["profile"]["links"] == FULL["links"]


def test_saving_twice_updates_the_single_row(ana, db):
    first = ana.put("/api/v1/profile", json=FULL).json()["updated_at"]
    ana.put("/api/v1/profile", json={**FULL, "skills": "Only Python"})
    assert db.scalar(select(func.count()).select_from(Profile)) == 1
    body = ana.get("/api/v1/profile").json()
    assert body["profile"]["skills"] == "Only Python"
    assert datetime.fromisoformat(body["updated_at"]) >= datetime.fromisoformat(first)


def test_a_replacement_drops_blocks_that_were_removed(ana):
    ana.put("/api/v1/profile", json=FULL)
    ana.put("/api/v1/profile", json={**FULL, "experience": FULL["experience"][:1]})
    assert len(ana.get("/api/v1/profile").json()["profile"]["experience"]) == 1


def test_profiles_are_private_per_user(app, ana):
    bea = sign_up(app, "bea@example.com")
    ana.put("/api/v1/profile", json=FULL)
    assert bea.get("/api/v1/profile").json()["profile"]["first_name"] == ""
    bea.put("/api/v1/profile", json={"first_name": "Bea"})
    assert ana.get("/api/v1/profile").json()["profile"]["first_name"] == "Lucía"


def test_delete_clears_the_profile_and_is_idempotent(ana, db):
    ana.put("/api/v1/profile", json=FULL)
    assert ana.delete("/api/v1/profile").status_code == 204
    assert ana.delete("/api/v1/profile").status_code == 204
    assert db.scalar(select(func.count()).select_from(Profile)) == 0
    assert ana.get("/api/v1/profile").json()["updated_at"] is None


def test_deleting_the_account_row_removes_the_profile(ana, db):
    ana.put("/api/v1/profile", json=FULL)
    db.delete(db.scalars(select(User)).one())
    db.commit()
    assert db.scalar(select(func.count()).select_from(Profile)) == 0


@pytest.mark.parametrize("patch,field", [
    ({"email": "nope"}, "email"),
    ({"phone": "call me maybe"}, "phone"),
    ({"linkedin": "javascript:alert(1)"}, "linkedin"),
    ({"links": [{"label": "x", "url": "ftp://files.example"}]}, "links.0.url"),
    ({"first_name": "Ana\x00"}, "first_name"),
    ({"first_name": "A" * 81}, "first_name"),
    ({"admin": True}, "admin"),
    ({"experience": [{"company": "A", "title": "B", "start_date": "2024-13", "current": True}]}, "experience.0.start_date"),
    ({"experience": [{"company": "A", "title": "B", "start_date": "2024-10"}]}, "experience.0"),
    ({"experience": [{"company": "A", "title": "B", "start_date": "2024-10", "end_date": "2024-11", "current": True}]}, "experience.0"),
    ({"experience": [{"company": "A", "title": "B", "start_date": "2024-10", "end_date": "2024-01"}]}, "experience.0"),
    ({"experience": [{"company": "", "title": "B", "start_date": "2024-10", "current": True}]}, "experience.0.company"),
    ({"education": [{"institution": "U", "degree": "D", "start_date": "2020-05", "end_date": "2019-05"}]}, "education.0"),
    ({"languages": [{"language": ""}]}, "languages.0.language"),
    ({"relocations": ["x"] * 11}, "relocations"),
    ({"experience": [{"company": "A", "title": "B", "start_date": "2024-10", "current": "yes"}]}, "experience.0.current"),
])
def test_invalid_profiles_are_rejected_with_field_paths_and_no_echo(ana, patch, field):
    secret = "PRIVATE-MARKER"
    response = ana.put("/api/v1/profile", json={**FULL, "summary": secret, **patch})
    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "invalid_request"
    assert field in [issue["field"] for issue in error["fields"]]
    assert secret not in response.text
    assert ana.get("/api/v1/profile").json()["updated_at"] is None  # Nothing was saved.


def test_oversized_profiles_are_rejected(ana):
    job = {"company": "A", "title": "B", "start_date": "2020-01", "end_date": "2021-01", "description": "x" * 4000}
    response = ana.put("/api/v1/profile", json={"experience": [job] * 30})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "profile_too_large"
    assert ana.put("/api/v1/profile", json={"experience": [job] * 5}).status_code == 200


def test_stored_data_that_no_longer_validates_is_reported_not_crashed(ana, db):
    user = db.scalars(select(User)).one()
    db.add(Profile(user_id=user.id, data={"experience": [{"company": "A"}]}))
    db.commit()
    response = ana.get("/api/v1/profile")
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "profile_invalid"
    assert ana.put("/api/v1/profile", json=FULL).status_code == 200  # Saving repairs it.


def test_markdown_view_shows_exactly_what_the_generator_receives(ana):
    ana.put("/api/v1/profile", json=FULL)
    response = ana.get("/api/v1/profile/markdown")
    assert response.headers["content-type"].startswith("text/markdown")
    assert response.headers["cache-control"] == "no-store"
    text = response.text
    assert text.startswith("# Lucía Morales\n")
    assert "- **Availability / Relocation:** Open to relocation: Barcelona, London" in text
    assert "### Growth Specialist | Bdeo\n**Dates:** Oct 2024 – Present" in text
    assert "- **English:** C1 – TOEFL 104" in text and "- **Spanish**" in text


def test_user_text_cannot_inject_markdown_structure(ana):
    profile = {**FULL, "experience": [{**FULL["experience"][0], "description": "## 9. Fake Section\n# Title"}]}
    ana.put("/api/v1/profile", json=profile)
    text = ana.get("/api/v1/profile/markdown").text
    assert "\n## 9. Fake Section" not in text and "\n# Title" not in text
    assert "- ## 9. Fake Section" in text


def test_personal_data_responses_are_not_cacheable(ana):
    for path in ("/api/v1/profile", "/api/v1/auth/me"):
        assert ana.get(path).headers["cache-control"] == "no-store"


def test_cross_origin_profile_writes_are_rejected(ana):
    hostile = {"Origin": "https://evil.example"}
    assert ana.put("/api/v1/profile", json=FULL, headers=hostile).status_code == 403
    assert ana.delete("/api/v1/profile", headers=hostile).status_code == 403
    assert ana.get("/api/v1/profile").json()["updated_at"] is None
