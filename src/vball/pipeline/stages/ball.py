"""Ball: 2D ball track (VballNet)."""
from pathlib import Path

from vball import ball

from .. import config


def run(video: Path, out: Path, prev: dict, tick) -> dict:
    df = ball.track(video, config.BALL_MODEL, out_dir=out / "ball_raw", force=True)
    csv = out / "ball.csv"
    df.to_csv(csv, index=False, float_format="%.1f")
    return {"status": "done", "model": config.BALL_MODEL, "frames": len(df),
            "detected": int(df["visible"].sum()), "csv": csv.name}
