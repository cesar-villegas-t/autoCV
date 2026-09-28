import json
from pathlib import Path
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient
from apps.api.main import create_app
from autocv.application.generation import Generator
from autocv.config import Settings
from autocv.infrastructure.llm.gemini import ProviderError
from tests.fixtures.resume import sample_resume
from tests.integration.conftest import sign_up


@pytest.fixture
def setup(tmp_path, make_app):
    settings = Settings(api_key="test-only", output_dir=tmp_path,
                        cors_origins=("http://localhost:5173",))

    def compile_pdf(tex, name, destination):
        assert r"\documentclass" in tex.read_text(encoding="utf-8")
        destination.mkdir(parents=True, exist_ok=True)
        pdf = destination / name
        pdf.write_bytes(b"%PDF-1.4\nmock")
        return pdf

    llm = Mock(return_value=json.dumps(sample_resume()))
    compiler = Mock(side_effect=compile_pdf)
    generator = Generator(settings, llm=llm, compiler=compiler)
    app = make_app(generator=generator, api_key="test-only")
    yield sign_up(app), llm, compiler


BODY = {"profile_text": "Candidate facts", "offer_text": "Job requirements", "output_name": "candidate.pdf"}


@pytest.mark.parametrize("code", ["provider_http_400", "provider_http_403", "provider_http_404", "provider_http_429", "provider_network", "provider_timeout", "provider_tls", "provider_token_limit"])
def test_provider_diagnostic_reaches_api_without_sensitive_data(setup, caplog, code):
    client, llm, compiler = setup
    llm.side_effect = ProviderError(code, "Safe diagnostic.")
    response = client.post("/api/v1/cv/generations", json=BODY)
    assert response.status_code == 502
    assert response.json()["error"]["code"] == code
    assert code in caplog.text
    assert BODY["profile_text"] not in caplog.text
    assert "test-only" not in caplog.text
    compiler.assert_not_called()


def test_health_and_generation_download(setup):
    client, llm, compiler = setup
    assert client.get("/api/v1/health").json() == {"status": "ok"}
    response = client.post("/api/v1/cv/generations", json=BODY)
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "completed"
    pdf = client.get(body["download_url"])
    assert pdf.status_code == 200
    assert pdf.headers["content-type"] == "application/pdf"
    assert pdf.content.startswith(b"%PDF")
    assert "candidate.pdf" in pdf.headers["content-disposition"]
    assert llm.call_count == compiler.call_count == 1
    second = client.post("/api/v1/cv/generations", json=BODY).json()
    assert second["id"] != body["id"]
    assert client.get(body["download_url"]).status_code == 200


@pytest.mark.parametrize("change", [
    {"output_name": "../secret.pdf"}, {"output_name": "C:\\secret.pdf"},
    {"output_name": "x:secret.pdf"}, {"profile_text": " "},
    {"offer_text": None}, {"profile_text": 12}, {"unexpected": "PRIVATE"},
    {"offer_text": "x" * 100_001},
])
def test_invalid_request_never_echoes_data_or_calls_provider(setup, change):
    client, llm, _ = setup
    response = client.post("/api/v1/cv/generations", json={**BODY, **change})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_request"
    assert "PRIVATE" not in response.text
    llm.assert_not_called()


@pytest.mark.parametrize("stage,status,code", [("provider", 502, "provider_error"),
                                              ("invalid", 502, "invalid_cv"),
                                              ("compiler", 500, "compilation_error")])
def test_safe_failures(setup, stage, status, code):
    client, llm, compiler = setup
    if stage == "provider":
        llm.side_effect = RuntimeError("PRIVATE secret-key C:\\internal")
    elif stage == "invalid":
        llm.return_value = '{"private": "PRIVATE"}'
    else:
        compiler.side_effect = RuntimeError("PRIVATE tex log")
    response = client.post("/api/v1/cv/generations", json=BODY)
    assert response.status_code == status
    assert response.json()["status"] == "failed"
    assert response.json()["error"]["code"] == code
    assert response.json()["id"]
    assert response.json()["download_url"] is None
    assert "PRIVATE" not in response.text


def test_missing_key(tmp_path):
    with TestClient(create_app(Settings(output_dir=tmp_path))) as client:
        response = client.post("/api/v1/cv/generations", json=BODY)
        assert response.status_code == 503
        assert response.json()["error"]["code"] == "not_configured"


def test_download_not_found_and_cors(setup):
    client, _, _ = setup
    assert client.get("/api/v1/cv/generations/00000000-0000-0000-0000-000000000000/pdf").status_code == 404
    assert client.get("/api/v1/cv/generations/not-a-uuid/pdf").status_code == 422
    allowed = client.options("/api/v1/cv/generations", headers={
        "Origin": "http://localhost:5173", "Access-Control-Request-Method": "POST"})
    assert allowed.headers["access-control-allow-origin"] == "http://localhost:5173"
    denied = client.get("/api/v1/health", headers={"Origin": "https://untrusted.example"})
    assert "access-control-allow-origin" not in denied.headers
