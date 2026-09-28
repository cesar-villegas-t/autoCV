"""Shared synchronous use case; injected adapters keep tests offline."""
from dataclasses import dataclass
import logging
from pathlib import Path
from typing import Callable
from uuid import uuid4

from autocv.config import Settings
from autocv.domain.files import normalized_pdf_name
from autocv.domain.models import parse_resume
from autocv.infrastructure.latex.compiler import compile_and_copy_pdf
from autocv.infrastructure.latex.renderer import render
from autocv.infrastructure.llm.gemini import ProviderError, call_gemini
from autocv.prompts.resume import prompt

logger = logging.getLogger(__name__)


class GenerationError(RuntimeError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class GenerationResult:
    id: str
    pdf_path: Path
    tex_path: Path


class Generator:
    def __init__(self, settings: Settings, *,
                 llm: Callable[[str, str, str], str] = call_gemini,
                 compiler: Callable[[Path, str, Path], Path] = compile_and_copy_pdf):
        self.settings = settings
        self.llm = llm
        self.compiler = compiler

    def generate_cv(self, *, profile_text: str, offer_text: str,
                    output_name: str = "cv.pdf", model: str | None = None,
                    tex_output: Path | None = None) -> GenerationResult:
        final_name = normalized_pdf_name(output_name)
        if not profile_text.strip() or not offer_text.strip():
            raise ValueError("Profile and offer must not be empty.")
        if not self.settings.api_key:
            raise GenerationError("not_configured", "Set GEMINI_API_KEY before generating a CV.")
        generation_id = str(uuid4())
        # Each request owns its directory, including concurrent equal filenames.
        directory = self.settings.output_dir / generation_id
        tex_path = tex_output if tex_output is not None else directory / "intermediate" / "cv.tex"
        try:
            raw = self.llm(self.settings.api_key, prompt(offer_text, profile_text), model or self.settings.model)
        except ProviderError as exc:
            logger.warning("CV generation failed: %s", exc.code)
            raise GenerationError(exc.code, str(exc)) from None
        except Exception:
            logger.warning("CV generation failed: provider_error")
            raise GenerationError("provider_error", "The CV provider could not complete the request.") from None
        try:
            resume = parse_resume(raw)
        except ValueError:
            raise GenerationError("invalid_cv", "The provider returned an invalid CV.") from None
        try:
            tex_path.parent.mkdir(parents=True, exist_ok=True)
            tex_path.write_text(render(resume), encoding="utf-8", newline="\n")
            pdf_path = self.compiler(tex_path, final_name, directory)
        except Exception:
            raise GenerationError("compilation_error", "Could not create a verified one-page PDF. Check the local LaTeX installation and CV length.") from None
        return GenerationResult(generation_id, pdf_path, tex_path.resolve())
