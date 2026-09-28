from pathlib import Path

def resolve_file(value: str, alternatives: tuple[str, ...], label: str) -> Path:
    for candidate in (value, *alternatives):
        if (path := Path(candidate)).is_file():
            return path
    raise FileNotFoundError(f"Could not find the {label}. Tried: {', '.join((value, *alternatives))}")


def read_text(path: Path, label: str) -> str:
    try:
        text = path.read_text(encoding="utf-8-sig").strip()
    except UnicodeDecodeError as exc:
        raise ValueError(f"{label.capitalize()} must use UTF-8: {path}") from exc
    if not text:
        raise ValueError(f"{label.capitalize()} is empty: {path}")
    return text
