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
from vball import ball, players, trajectory
from vball.calibration import calibrate
from vball.paths import MODELS

STAGES = ("decode", "court", "ball", "players", "trajectory", "events", "rallies")
# share of total pipeline time, for the progress bar
# Stage messages are shown to users as-is: write them for a coach, not a developer.
WEIGHTS = {"decode": 0.1, "court": 0.05, "ball": 0.35, "players": 0.38, "trajectory": 0.02, "events": 0.05,
           "rallies": 0.05}
BALL_MODEL = "v4c"
COURT_MODEL = MODELS / "court_kpt_yolo26n.pt"
# best measured on SportsMOT volleyball (docs/results/player-tracking.md); weights download on first use
PLAYER_CFG = players.TrackerConfig(model=str(MODELS / "yolo26s.pt"), imgsz=960, tracker="botsort.yaml", det_fps=10.0)

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


def court_homography_at(court_result: dict | None):
    """frame -> court-to-image homography from the court stage (per shot), or None where it has none."""
    shots = [s for s in (court_result or {}).get("shots", []) if s.get("H") is not None]

    def at(frame: int):
        for s in shots:
            if s["start_frame"] <= frame <= s["end_frame"]:
                return np.array(s["H"], float)
        return None
    return at


def players_stage(video: Path, out: Path, prev: dict, tick) -> dict:
    n = prev["decode"].get("frames") or 0
    fps = prev["decode"].get("fps") or 30.0

    def frames():
        cap = cv2.VideoCapture(str(video))
        i = 0
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            yield frame
            i += 1
            if n and i % 50 == 0:
                tick(i / n)
        cap.release()

    df = players.track_frames(frames(), fps, PLAYER_CFG)
    df = players.place_on_court(df, court_homography_at(prev.get("court")))
    df.to_csv(out / "players.csv.gz", index=False, float_format="%.2f")
    placed = bool(df["placed"].any()) if len(df) else False
    res = {"status": "done", "model": PLAYER_CFG.label(), "tracks": int(df["track_id"].nunique()) if len(df) else 0,
           "rows": int(len(df)), "placed": placed}
    if not placed:
        res["message"] = "The court was not found, so everyone in view is kept and no court positions are given."
    return res


def ball_uv(out: Path, n_frames: int) -> np.ndarray:
    """(n_frames, 2) ball image positions, NaN where the ball was not detected."""
    import pandas as pd
    uv = np.full((n_frames, 2), np.nan)
    df = pd.read_csv(out / "ball.csv")
    df = df[(df["visible"] > 0) & (df["frame"] < n_frames)]
    uv[df["frame"].to_numpy(int)] = df[["x", "y"]].to_numpy(float)
    return uv


def trajectory_stage(video: Path, out: Path, prev: dict, tick) -> dict:
    """3D flights per camera shot whose court keypoints give a usable calibration.

    Reads `court.shots[*].keypoints` (14 x 2 image points of the k6y7r layout, null when not seen).
    Writes flights.json: per flight its frames, ballistic parameters, quality and derived values."""
    meta = prev["decode"]
    n, fps, size = meta.get("frames") or 0, meta.get("fps") or 30.0, (meta.get("width"), meta.get("height"))
    shots = [s for s in (prev.get("court") or {}).get("shots", []) if s.get("keypoints")]
    if not shots:
        (out / "flights.json").write_text("[]")
        return {"status": "done", "flights": 0, "calibrated_shots": 0,
                "message": "The camera could not be calibrated because the court was not found, so there are no 3D flights."}
    uv = ball_uv(out, n)
    flights, unusable = [], []
    for k, shot in enumerate(shots):
        tick(k / len(shots))
        kp = np.array([[np.nan, np.nan] if p is None else p for p in shot["keypoints"]], float)
        cal = calibrate(kp, size)
        if cal.status == "unusable":
            unusable.append(cal.reason)
            continue
        a, b = shot["start_frame"], shot["end_frame"]
        for rec in trajectory.reconstruct(cal.camera, uv[a:b + 1], fps):
            f = rec["fit"]
            flights.append({"start_frame": a + f.start, "end_frame": a + f.end, "p0": f.p0.tolist(), "v0": f.v0.tolist(),
                            "fit_px": f.fit_px, "depth_sd_m": f.depth_sd_m, "quality": f.quality, "reasons": f.reasons,
                            "derived": rec["derived"], "calibration": cal.status})
    (out / "flights.json").write_text(json.dumps(flights))
    res = {"status": "done", "flights": len(flights), "calibrated_shots": len(shots) - len(unusable),
           "low_quality": sum(f["quality"] == "low" for f in flights)}
    if unusable:
        res["message"] = f"{len(unusable)} of {len(shots)} camera shots could not be calibrated ({unusable[0]})."
    return res


def events(video: Path, out: Path, prev: dict, tick) -> dict:
    return {"status": "todo", "message": "Contacts and landings arrive with milestone M3."}


def rallies(video: Path, out: Path, prev: dict, tick) -> dict:
    return {"status": "todo", "message": "Rally detection and scoring arrive with milestone M3."}


FUNCS = {"decode": decode, "court": court, "ball": ball_stage, "players": players_stage,
         "trajectory": trajectory_stage, "events": events, "rallies": rallies}
VERSIONS = {"decode": "1", "court": "0.1", "ball": f"{BALL_MODEL}-1", "players": f"{PLAYER_CFG.label()}-1",
            "trajectory": "1", "events": "0.3", "rallies": "0.1"}


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
