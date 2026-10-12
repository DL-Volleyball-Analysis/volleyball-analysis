"""Reading and writing a video's results folder: one <stage>.json per stage plus the files stages write
(ball.csv, players.csv.gz, camera_motion.npz, flights.json, action_events.json)."""

import json
from pathlib import Path

import numpy as np
import pandas as pd

from vball import camera_motion, court_registration

from . import config


def stage_file(results: Path, stage: str) -> Path:
    return results / f"{stage}.json"


def load_stage(results: Path, stage: str) -> dict | None:
    f = stage_file(results, stage)
    return json.loads(f.read_text()) if f.exists() else None


def corrected_court(
    court: dict | None, decode: dict | None, corrections: list[dict], results: Path | None = None
) -> dict | None:
    """The court stage result with the user's corrections overlaid (never written to court.json). With the results
    folder, a correction follows the camera motion through its shot."""
    if not corrections or not court or court.get("status") != "done" or not decode:
        return court
    motion = motion_of(results) if results is not None else None
    return court_registration.apply_corrections(
        court, corrections, (decode["width"], decode["height"]), motion=motion, fps=decode.get("fps")
    )


def motion_of(out: Path) -> camera_motion.Motion | None:
    return camera_motion.load(out / config.MOTION_FILE)


def court_homography_at(court_result: dict | None, image_size: tuple[int, int] | None = None):
    """frame -> court-to-image homography from the court stage, or None where it has none."""
    return lambda frame: court_registration.mapping_at(court_result, frame, image_size)


def ball_points(out: Path) -> dict[int, np.ndarray]:
    """frame -> detected ball (x, y) from the ball stage, for the actors' ball prior."""
    p = out / "ball.csv"
    if not p.exists():
        return {}
    df = pd.read_csv(p)
    df = df[df["visible"] > 0]
    return {int(f): np.array([x, y]) for f, x, y in zip(df["frame"], df["x"], df["y"])}


def ball_uv(out: Path, n_frames: int) -> np.ndarray:
    """(n_frames, 2) ball image positions, NaN where the ball was not detected."""
    import pandas as pd

    uv = np.full((n_frames, 2), np.nan)
    df = pd.read_csv(out / "ball.csv")
    df = df[(df["visible"] > 0) & (df["frame"] < n_frames)]
    uv[df["frame"].to_numpy(int)] = df[["x", "y"]].to_numpy(float)
    return uv
