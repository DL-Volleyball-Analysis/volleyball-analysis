"""Staged analysis pipeline built on the `vball` package.

Each stage writes data/results/<video_id>/<stage>.json with its version and status. A rerun
from stage S recomputes S and everything after it; earlier stages are reused when their
version still matches, so a new court model does not redo ball tracking.
"""
import json
from pathlib import Path
from typing import Callable

import cv2
import numpy as np
from vball import ball
from vball.paths import MODELS

STAGES = ("decode", "court", "ball", "events", "rallies")
# share of total pipeline time, for the progress bar
# Stage messages are shown to users as-is: write them for a coach, not a developer.
WEIGHTS = {"decode": 0.15, "court": 0.1, "ball": 0.6, "events": 0.05, "rallies": 0.1}
BALL_MODEL = "v4c"
COURT_MODEL = MODELS / "court_kpt_yolo26n.pt"

SHOT_CUT_CORRELATION = 0.6  # HSV histogram correlation below this between frames = camera cut


def video_meta(path: Path) -> dict:
    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        raise ValueError(f"cannot open video: {path.name}")
    meta = {
        "fps": cap.get(cv2.CAP_PROP_FPS) or 30.0,
        "frames": int(cap.get(cv2.CAP_PROP_FRAME_COUNT)),
        "width": int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
        "height": int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
    }
    cap.release()
    return meta


def decode(video: Path, out: Path, prev: dict, tick) -> dict:
    """Metadata and camera shots; the court homography is estimated per shot."""
    meta = video_meta(video)
    cap = cv2.VideoCapture(str(video))
    cuts, last, i = [0], None, 0
    while cap.grab():
        ok, frame = cap.retrieve()
        if not ok:
            break
        hsv = cv2.cvtColor(cv2.resize(frame, (160, 90)), cv2.COLOR_BGR2HSV)
        h = cv2.normalize(cv2.calcHist([hsv], [0, 1], None, [16, 8], [0, 180, 0, 256]), None).ravel()
        if last is not None and cv2.compareHist(last, h, cv2.HISTCMP_CORREL) < SHOT_CUT_CORRELATION:
            cuts.append(i)
        last, i = h, i + 1
        if i % 200 == 0 and meta["frames"]:
            tick(i / meta["frames"])
    cap.release()
    meta["frames"] = i  # container frame counts can be off; trust the decoded count
    shots = [{"start_frame": a, "end_frame": b - 1} for a, b in zip(cuts, cuts[1:] + [i])]
    return {"status": "done", **meta, "shots": shots}


def court(video: Path, out: Path, prev: dict, tick) -> dict:
    if not COURT_MODEL.exists():
        return {"status": "unavailable",
                "message": "The court model has not been trained yet."}
    return {"status": "todo", "message": "Court mapping arrives with milestone M1."}


def ball_stage(video: Path, out: Path, prev: dict, tick) -> dict:
    df = ball.track(video, BALL_MODEL, out_dir=out / "ball_raw", force=True)
    csv = out / "ball.csv"
    df.to_csv(csv, index=False, float_format="%.1f")
    return {"status": "done", "model": BALL_MODEL, "frames": len(df),
            "detected": int(df["visible"].sum()), "csv": csv.name}


def events(video: Path, out: Path, prev: dict, tick) -> dict:
    return {"status": "todo", "message": "Contacts and landings arrive with milestone M3."}


def rallies(video: Path, out: Path, prev: dict, tick) -> dict:
    return {"status": "todo", "message": "Rally detection and scoring arrive with milestone M3."}


FUNCS = {"decode": decode, "court": court, "ball": ball_stage, "events": events, "rallies": rallies}
VERSIONS = {"decode": "1", "court": "0.1", "ball": f"{BALL_MODEL}-1", "events": "0.1", "rallies": "0.1"}


def stage_file(results: Path, stage: str) -> Path:
    return results / f"{stage}.json"


def load_stage(results: Path, stage: str) -> dict | None:
    f = stage_file(results, stage)
    return json.loads(f.read_text()) if f.exists() else None


def run(video: Path, results: Path, from_stage: str = "decode",
        on_progress: Callable[[str, float], None] = lambda stage, p: None) -> dict:
    """Run the pipeline; returns {stage: result}. Raises on the first failing stage."""
    if from_stage not in STAGES:
        raise ValueError(f"unknown stage {from_stage!r}; stages are {STAGES}")
    results.mkdir(parents=True, exist_ok=True)
    start = STAGES.index(from_stage)
    done_weight, rerun, out = 0.0, False, {}
    for k, stage in enumerate(STAGES):
        cached = load_stage(results, stage)
        rerun = rerun or k >= start or cached is None or cached.get("version") != VERSIONS[stage]
        if rerun:
            def tick(frac, stage=stage, base=done_weight):
                on_progress(stage, base + WEIGHTS[stage] * float(np.clip(frac, 0, 1)))
            tick(0)
            res = {"version": VERSIONS[stage], **FUNCS[stage](video, results, out, tick)}
            stage_file(results, stage).write_text(json.dumps(res))
            cached = res
        out[stage] = cached
        done_weight += WEIGHTS[stage]
        on_progress(stage, done_weight)
    return out
