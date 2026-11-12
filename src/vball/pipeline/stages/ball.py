"""Ball: 2D ball track with VballNet V4c; WASB with gym weights for still cameras when config.GYM_BALL_FOR_STILL is on."""

from pathlib import Path

from vball import ball, court_registration
from vball.manifest import usable

from .. import config, models, results


def still_camera(prev: dict, out: Path) -> bool:
    """Whether every camera shot of the video is still (vball.court_registration.still on the decode stage's motion)."""
    meta = prev.get("decode") or {}
    size = (meta.get("width") or 1, meta.get("height") or 1)
    shots = meta.get("shots") or [{"start_frame": 0, "end_frame": max(0, (meta.get("frames") or 1) - 1)}]
    motion = results.motion_of(out)
    return all(court_registration.still(motion, sh["start_frame"], sh["end_frame"], size) for sh in shots)


def run(video: Path, out: Path, prev: dict, tick) -> dict:
    if config.GYM_BALL_FOR_STILL and still_camera(prev, out) and usable(config.GYM_BALL_MODEL):
        model = config.GYM_BALL_MODEL.stem
        df = models.gym_ball_track(video, config.GYM_BALL_MODEL, config.GYM_BALL_CHUNK, tick)
        why = "still camera"
    else:
        model = config.BALL_MODEL
        df = ball.track(video, config.BALL_MODEL, out_dir=out / "ball_raw", force=True)
        why = (
            "default model"
            if not config.GYM_BALL_FOR_STILL
            else "moving camera"
            if usable(config.GYM_BALL_MODEL)
            else "gym ball model not installed"
        )
    csv = out / "ball.csv"
    df.to_csv(csv, index=False, float_format="%.1f")
    return {
        "status": "done",
        "model": model,
        "model_reason": why,
        "frames": len(df),
        "detected": int(df["visible"].sum()),
        "csv": csv.name,
    }
