"""CLI adapter for the same generation use case as HTTP."""
import argparse
import sys
from pathlib import Path

from autocv.application.generation import Generator
from autocv.config import Settings
from autocv.infrastructure.files import read_text, resolve_file


def arguments(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a truthful one-page CV with Gemini.")
    parser.add_argument("--profile", default="profiles/profile.example.md")
    parser.add_argument("--offer", default="offers/oferta_de_empleo_marketing_bankinter.md")
    parser.add_argument("--output-name", default="bankinter_python_cv.pdf")
    parser.add_argument("--model", default=None)
    parser.add_argument("--tex-output", "--output", dest="tex_output", type=Path)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = arguments(argv)
    try:
        profile = read_text(resolve_file(args.profile, (), "profile"), "profile")
        offer = read_text(resolve_file(args.offer, ("offer_revolut.md", "offers/revolut.md"), "job offer"), "job offer")
        result = Generator(Settings.from_env()).generate_cv(
            profile_text=profile, offer_text=offer, output_name=args.output_name,
            model=args.model, tex_output=args.tex_output,
        )
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    print(f"Created LaTeX: {result.tex_path}")
    print(f"Created PDF: {result.pdf_path}")
    return 0
