import re
import shutil
import subprocess
from pathlib import Path
from autocv.domain.files import normalized_pdf_name

def compile_and_copy_pdf(tex_file: Path, final_name: str,
                         destination_dir: Path) -> Path:
    """Compile a LaTeX file and copy its PDF to the final output directory."""
    final_name = normalized_pdf_name(final_name)
    compiler = shutil.which("pdflatex")
    if not compiler:
        raise RuntimeError("pdflatex was not found. Install a LaTeX distribution and add it to PATH.")

    tex_file = tex_file.resolve()
    command = [
        compiler,
        "-interaction=nonstopmode",
        "-halt-on-error",
        "-file-line-error",
        "-no-shell-escape",
        f"-output-directory={tex_file.parent}",
        str(tex_file),
    ]
    try:
        result = subprocess.run(
            command,
            cwd=tex_file.parent,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=120,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        raise RuntimeError("Could not run pdflatex.") from None
    if result.returncode != 0:
        raise RuntimeError("LaTeX compilation failed; inspect the local compilation log.")
    page_match = re.search(r"Output written on.*?\((\d+) pages?,", result.stdout, re.DOTALL)
    if not page_match:
        raise RuntimeError("pdflatex completed, but the PDF page count could not be verified.")
    if page_match.group(1) != "1":
        raise RuntimeError(
            f"The generated CV has {page_match.group(1)} pages; the required output is exactly one page."
        )

    compiled_pdf = tex_file.with_suffix(".pdf")
    if not compiled_pdf.is_file():
        raise RuntimeError(f"pdflatex completed without creating {compiled_pdf.name}.")

    destination_dir.mkdir(parents=True, exist_ok=True)
    destination = destination_dir / normalized_pdf_name(final_name)
    shutil.copy2(compiled_pdf, destination)
    return destination.resolve()
