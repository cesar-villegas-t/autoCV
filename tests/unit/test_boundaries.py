import io
import json
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import Mock, patch
from urllib.error import HTTPError, URLError

import pytest
from autocv import cli
from autocv.application.generation import GenerationError, GenerationResult, Generator
from autocv.config import Settings
from autocv.domain.files import normalized_pdf_name
from autocv.domain.models import parse_resume
from autocv.infrastructure.latex import compiler
from autocv.infrastructure.llm import gemini
from tests.fixtures.resume import sample_resume


@pytest.mark.parametrize("code,retries", [(400, 1), (401, 1), (403, 1), (404, 1),
    (409, 1), (422, 1), (408, 3), (429, 3), (500, 3), (502, 3), (503, 3), (504, 3)])
def test_retry_only_transient_errors(code, retries):
    error = HTTPError("https://example.test/PRIVATE", code, "PRIVATE", {}, io.BytesIO(b'PRIVATE'))
    with patch.object(gemini, "urlopen", side_effect=error) as call, patch.object(gemini.time, "sleep"):
        with pytest.raises(RuntimeError) as caught:
            gemini.call_gemini("PRIVATE", "prompt", "model")
    assert call.call_count == retries
    assert "PRIVATE" not in str(caught.value)
    assert caught.value.code == f"provider_http_{code}"
    assert "PRIVATE" not in call.call_args.args[0].full_url


def test_transient_network_failure_then_success():
    response = Mock()
    response.read.return_value = b'{"candidates":[{"content":{"parts":[{"text":"{}"}]}}]}'
    context = Mock()
    context.__enter__ = Mock(return_value=response)
    context.__exit__ = Mock(return_value=False)
    with patch.object(gemini, "urlopen", side_effect=[URLError("PRIVATE"), context]) as call, \
         patch.object(gemini.time, "sleep"):
        assert gemini.call_gemini("PRIVATE", "prompt", "model") == "{}"
    assert call.call_count == 2


@pytest.mark.parametrize("filename", ["CON.pdf", "aux", "LPT1.pdf", "C:foo.pdf", "/foo.pdf",
    "foo.pdf:stream", "foo\x00.pdf", "a\\b.pdf", "a/b.pdf", "x.", "a?.pdf"])
def test_portable_path_rejection(filename):
    with pytest.raises(ValueError):
        normalized_pdf_name(filename)


def test_config_environment_only(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "PRIVATE")
    monkeypatch.setenv("AUTOCV_CORS_ORIGINS", "https://example.com,http://localhost:5173")
    with patch.object(Path, "read_text", side_effect=AssertionError("No credential reads")):
        settings = Settings.from_env()
    assert settings.api_key == "PRIVATE"
    assert "PRIVATE" not in repr(settings)
    assert len(settings.cors_origins) == 2
    monkeypatch.delenv("GEMINI_API_KEY")
    assert Settings.from_env().api_key == ""


@pytest.mark.parametrize("origin", ["*", "https://*.example.com", "https://example.com/path", "file://host"])
def test_cors_config_rejects_open_origins(origin):
    with pytest.raises(ValueError):
        Settings(cors_origins=(origin,))


def test_strict_nested_models():
    for change in ({"extra": "x"}, {"bullets": [1]}, {"title": None}):
        data = sample_resume()
        data["experience"][0].update(change)
        with pytest.raises(ValueError):
            parse_resume(json.dumps(data))


@pytest.mark.parametrize("stdout,returncode", [("No page information", 0), ("PRIVATE log", 1)])
def test_compiler_failure_never_publishes(tmp_path, stdout, returncode):
    with patch.object(compiler.shutil, "which", return_value="pdflatex"), \
         patch.object(compiler.subprocess, "run", return_value=Mock(stdout=stdout, returncode=returncode)), \
         patch.object(compiler.shutil, "copy2") as copy:
        with pytest.raises(RuntimeError) as caught:
            compiler.compile_and_copy_pdf(tmp_path / "cv.tex", "cv.pdf", tmp_path / "final")
    assert "PRIVATE" not in str(caught.value)
    copy.assert_not_called()


def test_generator_rejects_unsafe_filename_before_provider(tmp_path):
    llm = Mock()
    generator = Generator(Settings(api_key="test", output_dir=tmp_path), llm=llm)
    with pytest.raises(ValueError):
        generator.generate_cv(profile_text="profile", offer_text="offer", output_name="../x.pdf")
    llm.assert_not_called()


def test_cli_shared_use_case_and_legacy_alias(tmp_path):
    profile, offer = tmp_path / "profile.md", tmp_path / "offer.md"
    profile.write_text("profile", encoding="utf-8")
    offer.write_text("offer", encoding="utf-8")
    result = GenerationResult("id", tmp_path / "cv.pdf", tmp_path / "custom.tex")
    with patch.object(cli, "Generator") as factory, redirect_stdout(io.StringIO()):
        factory.return_value.generate_cv.return_value = result
        assert cli.main(["--profile", str(profile), "--offer", str(offer),
                         "--output", str(result.tex_path), "--output-name", "cv.pdf", "--model", "custom"]) == 0
    factory.return_value.generate_cv.assert_called_once_with(
        profile_text="profile", offer_text="offer", output_name="cv.pdf", model="custom", tex_output=result.tex_path)


def test_cli_missing_key_returns_safe_error(tmp_path, monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    profile = tmp_path / "profile.md"
    profile.write_text("example", encoding="utf-8")
    stderr = io.StringIO()
    with redirect_stderr(stderr):
        assert cli.main(["--profile", str(profile), "--offer", str(profile)]) == 1
    assert "GEMINI_API_KEY" in stderr.getvalue()


def test_database_url_is_environment_only_and_never_in_repr(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://user:PRIVATE@localhost/db")
    settings = Settings.from_env()
    assert settings.database_url.endswith("/db")
    assert "PRIVATE" not in repr(settings)
    monkeypatch.delenv("DATABASE_URL")
    assert Settings.from_env().database_url == ""
