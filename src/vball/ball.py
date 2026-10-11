"""Ball tracking with VballNet ONNX models.

Two methods, same output columns:
    track(video, model)          upstream script (kept unmodified in external/), whole frame at 512 x 288
    track_refined(video, det)    a detector's candidates (vball.ball_detect), fixed objects dropped, linked
                                 over time, short gaps filled (vball.ball_track)
    -> DataFrame[frame, visible, x, y, radius]
"""
import subprocess
import sys
from pathlib import Path

import cv2
import pandas as pd

from .paths import BALL_MODELS, OUTPUTS, VBALLNET_SRC


def track(video: Path, model: str = "v4c", out_dir: Path | None = None, force: bool = False) -> pd.DataFrame:
    """Run ball detection on a video and return one row per frame."""
    video = Path(video)
    model_path = BALL_MODELS.get(model, Path(model))
    out_dir = Path(out_dir or OUTPUTS / "ball_tracks" / model)
    csv = out_dir / video.stem / "ball.csv"
    if force or not csv.exists():
        out_dir.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            [sys.executable, "inference_onnx_seq_gray_v2.py",
             "--video_path", str(video.resolve()), "--model_path", str(Path(model_path).resolve()),
             "--output_dir", str(out_dir.resolve()), "--only_csv"],
            cwd=VBALLNET_SRC, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
    return load(csv)


def load(csv: Path) -> pd.DataFrame:
    """Read an upstream ball.csv into lowercase columns; missing detections become NaN."""
    df = pd.read_csv(csv).rename(columns=str.lower)
    df = df.rename(columns={"visibility": "visible"})
    hidden = df["visible"] <= 0
    df.loc[hidden, ["x", "y"]] = float("nan")
    df["visible"] = (~hidden).astype(int)
    return df[["frame", "visible", "x", "y", "radius"]]


def read_frames(video: Path) -> list:
    cap = cv2.VideoCapture(str(video))
    frames = []
    while True:
        ok, f = cap.read()
        if not ok:
            break
        frames.append(f)
    cap.release()
    return frames


def track_refined(video: Path, detector: str = "ravel012", cfg=None) -> pd.DataFrame:
    """Ball track from a detector's candidates with the fixed-object check, linking and gap filling
    (vball.ball_detect, vball.ball_track). Reads the whole video: meant for clips and shots, not full matches."""
    from . import ball_detect
    from .ball_track import TrackConfig, track as link_track
    frames = read_frames(Path(video))
    return link_track(frames, ball_detect.load(detector).candidates(frames), cfg or TrackConfig())
