"""Rally cues for fixed-camera matches from the pipeline's own stages (change label-rallies-from-score, task 2.1).

For every full match in a folder: the web app pipeline's decode (shots, camera motion), court (line evidence for
still shots) and ball (VballNet) stages run into results/<video stem>/, people are detected twice a second with the
pipeline's general person detector (the player-only one sees too few people in end-line views), and
`vball.rally_cues.stage_cues` turns them into cues for every camera shot whose court is ok. Using the stages
themselves keeps the training cues identical to what the rallies stage computes.

  .venv/bin/python scripts/extract_stage_cues.py              # data/datasets/watchdog/videos -> .../cues/<stem>.csv
"""
import argparse
import json
import sys
from pathlib import Path

import cv2
import numpy as np
import pandas as pd

from vball import court_registration
from vball.paths import DATASETS
from vball.rally_cues import stage_cues

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "webapp" / "backend"))
import pipeline  # noqa: E402

PEOPLE_FPS = 2.0


def detect_people(video: Path, fps: float, n: int, every: int) -> pd.DataFrame:
    """Person boxes on every `every`-th frame with the pipeline's general detector and settings."""
    from ultralytics import YOLO
    model = YOLO(str(pipeline.GENERAL_PLAYER_MODEL))
    cap, rows, i = cv2.VideoCapture(str(video)), [], 0
    while i < n:
        if i % every:
            if not cap.grab():
                break
            i += 1
            continue
        ok, frame = cap.read()
        if not ok:
            break
        r = model(frame, imgsz=pipeline.PLAYER_CFG.imgsz, conf=pipeline.PLAYER_CFG.conf, classes=[0], verbose=False)[0]
        for b in r.boxes.xyxy.cpu().numpy():
            rows.append((i, *b))
        i += 1
    cap.release()
    return pd.DataFrame(rows, columns=["frame", "x1", "y1", "x2", "y2"])


def match_cues(video: Path, out: Path) -> pd.DataFrame:
    out.mkdir(parents=True, exist_ok=True)
    prev = {}
    for name, fn in (("decode", pipeline.decode), ("court", pipeline.court), ("ball", pipeline.ball_stage)):
        res = pipeline.load_stage(out, name)
        if res is None or res.get("version") != pipeline.VERSIONS[name]:
            res = {"version": pipeline.VERSIONS[name], **fn(video, out, prev, lambda f: None)}
            pipeline.stage_file(out, name).write_text(json.dumps(res))
        prev[name] = res
    meta = prev["decode"]
    fps, n, size = meta["fps"], meta["frames"], (meta["width"], meta["height"])
    people_csv = out / "people.csv.gz"
    if people_csv.exists():
        people = pd.read_csv(people_csv)
    else:
        people = detect_people(video, fps, n, max(1, int(round(fps / PEOPLE_FPS))))
        people.to_csv(people_csv, index=False, float_format="%.1f")
    ball = pd.read_csv(out / "ball.csv")
    parts = []
    for shot in prev["court"].get("shots", []):
        if shot["status"] != "ok" or not shot["samples"]:
            continue
        a, b = shot["start_frame"], shot["end_frame"]
        H = court_registration.mapping_at(prev["court"], (a + b) // 2, size)
        sb = ball[(ball.frame >= a) & (ball.frame <= b)].copy()
        sp = people[(people.frame >= a) & (people.frame <= b)].copy()
        sb["frame"] -= a
        sp["frame"] -= a
        c = stage_cues(sb, sp, fps, b - a + 1, size, H)
        c["t"] = np.round(c["t"] + a / fps, 3)
        c["shot"] = len(parts)
        parts.append(c)
    return pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--videos", type=Path, default=DATASETS / "watchdog" / "videos")
    ap.add_argument("--results", type=Path, default=DATASETS / "watchdog" / "results")
    ap.add_argument("--out", type=Path, default=DATASETS / "watchdog" / "cues")
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    for video in sorted(args.videos.glob("*.mp4")):
        dst = args.out / f"{video.stem}.csv"
        if dst.exists():
            continue
        cues = match_cues(video, args.results / video.stem)
        cues.to_csv(dst, index=False)
        print(f"{video.stem}: {len(cues)} samples over {cues['shot'].nunique() if len(cues) else 0} ok shots", flush=True)


if __name__ == "__main__":
    main()
