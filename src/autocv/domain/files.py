"""Portable filename validation, including Windows device names and streams."""
import re
from pathlib import PurePosixPath, PureWindowsPath


def normalized_pdf_name(value: str) -> str:
    value = value.strip()
    if not value or value in {".", ".."} or len(value) > 120:
        raise ValueError("PDF filename must contain 1 to 120 characters.")
    if (PureWindowsPath(value).name != value or PurePosixPath(value).name != value
            or re.search(r'[<>:"/\\|?*\x00-\x1f\x7f]', value)
            or value.endswith((".", " "))):
        raise ValueError("PDF name must be a filename, not a path.")
    if re.fullmatch(r"(?i)(CON|PRN|AUX|NUL|COM[1-9¹²³]|LPT[1-9¹²³])", value.split('.')[0]):
        raise ValueError("Reserved PDF filename.")
    suffix = PurePosixPath(value).suffix
    if suffix and suffix.lower() != ".pdf":
        raise ValueError("PDF filename must use the .pdf extension.")
    return value if suffix else f"{value}.pdf"
