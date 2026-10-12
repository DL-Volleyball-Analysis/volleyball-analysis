"""Shared by the routers: the database, the video lookup and cached result tables."""

from functools import lru_cache
from typing import cast

import pandas as pd
from fastapi import HTTPException

from .db import Database
from .schemas import Team
from .settings import DB_PATH

db = Database(DB_PATH)


def video_or_404(vid: str) -> dict:
    v = db.get_video(vid)
    if v is None:
        raise HTTPException(404, "video not found")
    return v


def effective_winners(rows: list[dict]) -> list[Team | None]:
    """The user's correction wins over the model's winner."""
    return [cast(Team | None, r["winner_override"] or r["winner"]) for r in rows]  # the database holds a, b or null


@lru_cache(maxsize=8)
def ball_table(csv: str, mtime: float) -> pd.DataFrame:
    """ball.csv, cached per file version (path, modification time)."""
    return pd.read_csv(csv)


@lru_cache(maxsize=4)
def players_table(csv: str, mtime: float) -> pd.DataFrame:
    """players.csv.gz, cached per file version (path, modification time)."""
    return pd.read_csv(csv, keep_default_na=True)
