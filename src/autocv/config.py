"""Environment configuration; never read credential files."""
import os
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlsplit


@dataclass(frozen=True)
class Settings:
    api_key: str = field(default="", repr=False)
    model: str = "gemini-3.5-flash-lite"
    output_dir: Path = Path("output")
    cors_origins: tuple[str, ...] = ()

    def __post_init__(self):
        for origin in self.cors_origins:
            parsed = urlsplit(origin)
            if (parsed.scheme not in {"http", "https"} or not parsed.hostname
                    or parsed.path or parsed.query or parsed.fragment
                    or parsed.username or parsed.password or "*" in origin):
                raise ValueError("CORS requires explicit HTTP(S) origins without paths.")

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            api_key=os.getenv("GEMINI_API_KEY", "").strip(),
            model=os.getenv("AUTOCV_MODEL", "gemini-3.5-flash-lite"),
            output_dir=Path(os.getenv("AUTOCV_OUTPUT_DIR", "output")),
            cors_origins=tuple(x.strip() for x in os.getenv("AUTOCV_CORS_ORIGINS", "").split(",") if x.strip()),
        )
