"""Settings of the API and the worker, read once from the environment.

VBALL_WEBAPP_DATA   folder for uploads, analysis results and the job database (default: webapp/data)
VBALL_CORS_ORIGINS  comma-separated origins the browser app may call from (default: the Vite dev servers)
VBALL_LOG_LEVEL     DEBUG, INFO (default), WARNING or ERROR
VBALL_MODELS        folder with the model weights (read by vball.paths; default: models/ in the repository)
"""

import logging
import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    data: Path
    cors_origins: tuple[str, ...]
    log_level: str

    @classmethod
    def from_env(cls, env: Mapping[str, str] = os.environ) -> "Settings":
        level = env.get("VBALL_LOG_LEVEL", "INFO").upper()
        if level not in ("DEBUG", "INFO", "WARNING", "ERROR"):
            raise ValueError(f"VBALL_LOG_LEVEL must be DEBUG, INFO, WARNING or ERROR, not {level!r}")
        origins = env.get("VBALL_CORS_ORIGINS", "http://localhost:3000,http://localhost:5173")
        return cls(
            data=Path(env.get("VBALL_WEBAPP_DATA", Path(__file__).resolve().parents[2] / "data")),
            cors_origins=tuple(o.strip() for o in origins.split(",") if o.strip()),
            log_level=level,
        )


SETTINGS = Settings.from_env()
DATA = SETTINGS.data
UPLOADS = DATA / "uploads"
RESULTS = DATA / "results"
DB_PATH = DATA / "webapp.db"
VIDEO_SUFFIXES = {".mp4", ".mov", ".avi", ".mkv", ".m4v"}


def configure_logging() -> None:
    """One log format for the API and the worker (time, level, module, message)."""
    logging.basicConfig(level=SETTINGS.log_level, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
