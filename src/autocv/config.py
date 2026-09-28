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
    database_url: str = field(default="", repr=False)
    session_days: int = 7
    cookie_secure: bool = False

    def __post_init__(self):
        if not 1 <= self.session_days <= 90:
            raise ValueError("AUTOCV_SESSION_DAYS must be between 1 and 90.")
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
            database_url=os.getenv("DATABASE_URL", "").strip(),
            session_days=int(os.getenv("AUTOCV_SESSION_DAYS", "7")),
            cookie_secure=os.getenv("AUTOCV_COOKIE_SECURE", "").strip().lower() in {"1", "true", "yes"},
            cors_origins=tuple(x.strip() for x in os.getenv("AUTOCV_CORS_ORIGINS", "").split(",") if x.strip()),
        )
