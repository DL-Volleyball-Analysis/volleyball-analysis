"""Paths shared by the API and the worker (override with VBALL_WEBAPP_DATA)."""
import os
from pathlib import Path

DATA = Path(os.environ.get("VBALL_WEBAPP_DATA", Path(__file__).resolve().parents[1] / "data"))
UPLOADS = DATA / "uploads"
RESULTS = DATA / "results"
DB_PATH = DATA / "webapp.db"
VIDEO_SUFFIXES = {".mp4", ".mov", ".avi", ".mkv", ".m4v"}
