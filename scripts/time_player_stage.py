"""Time the web app's players stage (detection + tracking + interpolation) on the evaluation clips.

Uses the stage's own configuration (webapp/backend/pipeline.py PLAYER_CFG) and scales the measured
time to a 2-hour match at the same frame rate.

  .venv/bin/python scripts/time_player_stage.py
"""
import sys
import time
from pathlib import Path

import cv2

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "webapp" / "backend"))
import pipeline  # noqa: E402

from vball import players  # noqa: E402
from vball.paths import VIDEOS  # noqa: E402


def frames(path: Path):
    cap = cv2.VideoCapture(str(path))
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        yield frame
    cap.release()


def main():
    cfg = pipeline.PLAYER_CFG
    print(f"config {cfg.label()}")
    total_s = total_video_s = 0.0
    for clip in sorted(VIDEOS.glob("*.mp4")):
        cap = cv2.VideoCapture(str(clip))
        fps, n = cap.get(cv2.CAP_PROP_FPS) or 30.0, int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        cap.release()
        t0 = time.perf_counter()
        df = players.track_frames(frames(clip), fps, cfg)
        dt = time.perf_counter() - t0
        total_s, total_video_s = total_s + dt, total_video_s + n / fps
        print(f"{clip.stem:28s} {n:5d} frames at {fps:.0f} fps: {dt:6.1f} s ({dt / (n / fps):.2f}x real time), "
              f"{df['track_id'].nunique()} tracks")
    ratio = total_s / total_video_s
    print(f"overall {ratio:.2f}x real time -> a 2-hour match takes {2 * ratio:.1f} h for this stage")


if __name__ == "__main__":
    main()
