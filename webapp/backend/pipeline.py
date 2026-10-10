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
from vball import ball, court_registration, players, trajectory
from vball.calibration import calibrate
from vball.court_keypoints import detect as detect_keypoints
from vball.paths import MODELS

STAGES = ("decode", "court", "ball", "players", "trajectory", "events", "rallies")
# share of total pipeline time, for the progress bar
# Stage messages are shown to users as-is: write them for a coach, not a developer.
WEIGHTS = {"decode": 0.1, "court": 0.05, "ball": 0.35, "players": 0.38, "trajectory": 0.02, "events": 0.05,
           "rallies": 0.05}
BALL_MODEL = "v4c"
# the installed court keypoint model: copy the chosen weights here (models/ is not in git)
COURT_MODEL = MODELS / "court_kpt.pt"
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


def court_detector():
    """frame -> 14 x (x, y, conf) with the installed court model, at the size it was trained at.
    Tests replace this function with a fake detector."""
    from ultralytics import YOLO
    model = YOLO(str(COURT_MODEL))
    imgsz = int((getattr(model, "overrides", {}) or {}).get("imgsz", 640))
    return lambda frame: detect_keypoints(model, frame, imgsz)


def court(video: Path, out: Path, prev: dict, tick) -> dict:
    """Per-shot court registration (vball.court_registration) from the court keypoint model."""
    if not COURT_MODEL.exists():
        return {"status": "unavailable", "message": "The court model has not been trained yet."}
    meta = prev["decode"]
    fps, size = meta.get("fps") or 30.0, (meta.get("width"), meta.get("height"))
    shots = meta.get("shots") or [{"start_frame": 0, "end_frame": max(0, (meta.get("frames") or 1) - 1)}]
    wanted = sorted({f for sh in shots for f in court_registration.sample_frames(sh["start_frame"], sh["end_frame"], fps)})
    detect = court_detector()
    # one sequential pass: decode only the sampled frames
    keypoints, cap, i, k = {}, cv2.VideoCapture(str(video)), 0, 0
    while k < len(wanted) and cap.grab():
        if i == wanted[k]:
            ok, frame = cap.retrieve()
            if ok:
                keypoints[i] = detect(frame)
            k += 1
            if k % 10 == 0:
                tick(k / len(wanted))
        i += 1
    cap.release()
    empty = np.zeros((14, 3))
    registered = court_registration.register(shots, fps, size, lambda f: keypoints.get(f, empty))
    counts = {st: sum(r["status"] == st for r in registered) for st in ("ok", "needs_review", "failed")}
    res = {"status": "done", "model": COURT_MODEL.name, "shots": registered, "counts": counts}
    if counts["ok"] < len(registered):
        res["message"] = (f"Court found in {counts['ok']} of {len(registered)} camera shots"
                          f" ({counts['needs_review']} to check, {counts['failed']} not found).")
    return res


def ball_stage(video: Path, out: Path, prev: dict, tick) -> dict:
    df = ball.track(video, BALL_MODEL, out_dir=out / "ball_raw", force=True)
    csv = out / "ball.csv"
    df.to_csv(csv, index=False, float_format="%.1f")
    return {"status": "done", "model": BALL_MODEL, "frames": len(df),
            "detected": int(df["visible"].sum()), "csv": csv.name}


def court_homography_at(court_result: dict | None, image_size: tuple[int, int] | None = None):
    """frame -> court-to-image homography from the court stage, or None where it has none."""
    return lambda frame: court_registration.mapping_at(court_result, frame, image_size)


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
    size = (prev["decode"].get("width"), prev["decode"].get("height"))
    df = players.place_on_court(df, court_homography_at(prev.get("court"), size))
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
    """3D flights per camera shot that has a usable camera calibration.

    The calibration comes from the court stage's samples (raw keypoints, net points included): the first
    usable one, nearest the middle of the shot. Writes flights.json: per flight its frames, ballistic
    parameters, quality and derived values."""
    meta = prev["decode"]
    n, fps, size = meta.get("frames") or 0, meta.get("fps") or 30.0, (meta.get("width"), meta.get("height"))
    court_result = prev.get("court") or {}
    shots = [s for s in court_result.get("shots", []) if s.get("status") in court_registration.USABLE and s.get("samples")]
    if not shots:
        (out / "flights.json").write_text("[]")
        return {"status": "done", "flights": 0, "calibrated_shots": 0,
                "message": "The camera could not be calibrated because the court was not found, so there are no 3D flights."}
    uv = ball_uv(out, n)
    flights, unusable, rejected = [], [], []
    for k, shot in enumerate(shots):
        tick(k / len(shots))
        cal, reason = None, "no court keypoints for calibration"
        for sample in court_registration.calibration_samples(court_result, shot["start_frame"], shot["end_frame"]):
            kp = np.array(sample.get("keypoints") or [], float)
            if kp.shape != (14, 3):
                continue
            xy = np.where(kp[:, 2:3] >= 0.5, kp[:, :2], np.nan)  # unconfident keypoints count as unseen
            c = calibrate(xy, size)
            if c.status != "unusable":
                cal = c
                break
            reason = c.reason
        if cal is None:
            unusable.append(reason)
            continue
        a, b = shot["start_frame"], shot["end_frame"]
        for rec in trajectory.reconstruct(cal.camera, uv[a:b + 1], fps, rejected=rejected):
            f = rec["fit"]
            flights.append({"start_frame": a + f.start, "end_frame": a + f.end, "p0": f.p0.tolist(), "v0": f.v0.tolist(),
                            "fit_px": f.fit_px, "depth_sd_m": f.depth_sd_m, "quality": f.quality, "reasons": f.reasons,
                            "derived": rec["derived"], "calibration": cal.status})
    (out / "flights.json").write_text(json.dumps(flights))
    res = {"status": "done", "flights": len(flights), "calibrated_shots": len(shots) - len(unusable),
           "low_quality": sum(f["quality"] == "low" for f in flights), "rejected": len(rejected)}
    notes = []
    if unusable:
        notes.append(f"{len(unusable)} of {len(shots)} camera shots could not be calibrated ({unusable[0]}).")
    if rejected:
        notes.append(f"{len(rejected)} flights were left out as physically impossible ({rejected[0][2]}), "
                     "a sign that the camera calibration is off.")
    if notes:
        res["message"] = " ".join(notes)
    return res


def events(video: Path, out: Path, prev: dict, tick) -> dict:
    return {"status": "todo", "message": "Contacts and landings arrive with milestone M3."}


def rallies(video: Path, out: Path, prev: dict, tick) -> dict:
    return {"status": "todo", "message": "Rally detection and scoring arrive with milestone M3."}


FUNCS = {"decode": decode, "court": court, "ball": ball_stage, "players": players_stage,
         "trajectory": trajectory_stage, "events": events, "rallies": rallies}
VERSIONS = {"decode": "1", "court": "1", "ball": f"{BALL_MODEL}-1", "players": f"{PLAYER_CFG.label()}-2",  # -2: interpolation bridges short gaps only
            "trajectory": "2", "events": "0.3", "rallies": "0.1"}


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
