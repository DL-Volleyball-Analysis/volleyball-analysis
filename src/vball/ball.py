"""Ball tracking with VballNet ONNX models.

Inference itself is delegated to the upstream script (kept unmodified in external/),
so this module only standardises inputs and outputs:
    track(video, model) -> DataFrame[frame, visible, x, y, radius]
"""
import subprocess
import sys
from pathlib import Path

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
