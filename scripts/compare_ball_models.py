"""Compare VballNet ball models on every clip in data/videos.

Writes outputs/ball_model_comparison/{metrics.csv, trajectories.jpg}.
Usage: .venv/bin/python scripts/compare_ball_models.py [--models v4c fast_v1]
"""
import argparse
import sys
from pathlib import Path

import cv2
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from vball import ball, metrics  # noqa: E402
from vball.paths import OUTPUTS, VIDEOS  # noqa: E402

COLORS = {"fast_v1": (0, 0, 255), "v4c": (0, 255, 0)}


def mid_frame(video: Path):
    cap = cv2.VideoCapture(str(video))
    cap.set(cv2.CAP_PROP_POS_FRAMES, int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) // 2)
    ok, frame = cap.read()
    return frame


def overlay(frame, track, color, title):
    img = frame.copy()
    pts = track.dropna(subset=["x", "y"])[["x", "y"]].to_numpy(int)
    for a, b in zip(pts[:-1], pts[1:]):
        if np.hypot(*(a - b)) < 150:
            cv2.line(img, tuple(a), tuple(b), color, 3)
    for p in pts:
        cv2.circle(img, tuple(p), 6, color, -1)
    cv2.putText(img, title, (30, 70), cv2.FONT_HERSHEY_SIMPLEX, 1.8, (255, 255, 255), 5)
    return cv2.resize(img, (640, 360))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", nargs="+", default=["fast_v1", "v4c"])
    args = ap.parse_args()
    out = OUTPUTS / "ball_model_comparison"
    out.mkdir(parents=True, exist_ok=True)

    rows, tiles = [], []
    for video in sorted(VIDEOS.glob("*.mp4")):
        frame = mid_frame(video)
        width = frame.shape[1]
        row_tiles = []
        for m in args.models:
            t = ball.track(video, m)
            rows.append(dict(video=video.stem, model=m, frames=len(t),
                             detection_rate=round(metrics.detection_rate(t), 3),
                             jumps_per_100=round(metrics.jump_rate(t, width), 2)))
            row_tiles.append(overlay(frame, t, COLORS.get(m, (255, 255, 0)), f"{video.stem} | {m}"))
        tiles.append(np.hstack(row_tiles))

    df = pd.DataFrame(rows)
    df.to_csv(out / "metrics.csv", index=False)
    cv2.imwrite(str(out / "trajectories.jpg"), np.vstack(tiles))
    print(df.to_string(index=False))


if __name__ == "__main__":
    main()
