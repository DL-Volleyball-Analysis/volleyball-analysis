"""Staged analysis pipeline built on the `vball` package.

Each stage writes data/results/<video_id>/<stage>.json with its version and status. A rerun
from stage S recomputes S and everything after it; earlier stages are reused when their
version still matches, so a new court model does not redo ball tracking.
"""
import json
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path

import cv2
import numpy as np
import pandas as pd

from vball import actions, actors, ball, camera_motion, court_lines, court_registration, jersey, players, teams, trajectory
from vball import rallies as vrallies
from vball.calibration import calibrate
from vball.court_keypoints import detect as detect_keypoints
from vball.paths import MODELS

STAGES = ("decode", "court", "ball", "players", "actions", "trajectory", "events", "rallies")
# share of total pipeline time, for the progress bar
# Stage messages are shown to users as-is: write them for a coach, not a developer.
WEIGHTS = {"decode": 0.1, "court": 0.05, "ball": 0.3, "players": 0.33, "actions": 0.1, "trajectory": 0.02,
           "events": 0.05, "rallies": 0.05}
BALL_MODEL = "v4c"
# the installed court keypoint model: copy the chosen weights here (models/ is not in git)
# Every installed court model registers every shot; court_registration.pick keeps the best per shot. v2 is right
# on gym images (0.49 m) and v3b on broadcast clips (0.10 m); neither does both (docs/results/court-keypoints.md).
COURT_MODELS = {"gym": MODELS / "court_kpt.pt", "broadcast": MODELS / "court_kpt_broadcast.pt"}
# capstone action recogniser (test mAP@0.5 0.957, same matches as training) and the retrained digit detector;
# shirt numbers are read only once the digit model is installed (docs/results/actions.md)
RALLY_MODEL = MODELS / "rally_cues_hgb.joblib"  # docs/results/rallies.md
ACTION_MODEL = MODELS / "action_yolo11m.pt"  # serves (the person classifier has no serve class)
PERSON_MODEL = MODELS / "person_action_yolo26s_cls.pt"  # block / receive / set / spike per player (docs/results/actions.md)
BALL_PRIOR = actors.ActorConfig(k=2.0, floor=0.6)  # chosen on the Volleyball dataset's validation matches
JERSEY_MODEL = MODELS / "jersey_digits_yolo26s.pt"
ACTION_FPS, JERSEY_FPS = 10.0, 2.0
# YOLO26s fine-tuned on SportsMOT volleyball training sequences (players only): IDF1 0.690, precision 0.970 on
# SportsMOT volleyball val, against 0.484 / 0.614 for the COCO weights (docs/results/player-tracking.md)
GENERAL_PLAYER_MODEL = MODELS / "yolo26s.pt"  # COCO persons: fallback where the player-only detector misses players
PLAYER_CFG = players.TrackerConfig(model=str(MODELS / "player_yolo26s_sportsmot.pt"), imgsz=960, tracker="botsort.yaml", det_fps=10.0)

MOTION_FILE = "camera_motion.npz"
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
    """Metadata, camera shots and camera motion (vball.camera_motion, saved to camera_motion.npz); the court
    homography is estimated per shot and follows the motion within it."""
    meta = video_meta(video)
    cap = cv2.VideoCapture(str(video))
    cuts, last = [0], None

    def frames():
        nonlocal last
        i = 0
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
            yield frame

    steps, share = camera_motion.estimate(frames())
    cap.release()
    n = len(steps) if last is not None else 0
    for c in cuts[1:]:  # no motion across a cut
        steps[c], share[c] = np.eye(3), 0.0
    if n:
        camera_motion.save(out / MOTION_FILE, steps, share)
    meta["frames"] = n  # container frame counts can be off; trust the decoded count
    shots = [{"start_frame": a, "end_frame": b - 1} for a, b in zip(cuts, cuts[1:] + [n])]
    return {"status": "done", **meta, "shots": shots, "motion": MOTION_FILE if n else None,
            "motion_share": round(float(np.median(share[1:])), 3) if n > 1 else None}


def motion_of(out: Path) -> camera_motion.Motion | None:
    return camera_motion.load(out / MOTION_FILE)


def court_detector(weights: Path):
    """frame -> 14 x (x, y, conf) with one court model, at the size it was trained at.
    Tests replace this function with a fake detector."""
    from ultralytics import YOLO
    model = YOLO(str(weights))
    imgsz = int((getattr(model, "overrides", {}) or {}).get("imgsz", 640))
    return lambda frame: detect_keypoints(model, frame, imgsz)


def court(video: Path, out: Path, prev: dict, tick) -> dict:
    """Per-shot court registration (vball.court_registration) with every installed court model, keeping the
    best model per shot; shots with a still camera are then decided by line evidence on their background plate
    (vball.court_lines)."""
    models = {name: path for name, path in COURT_MODELS.items() if path.exists()}
    if not models:
        return {"status": "unavailable", "message": "The court model has not been trained yet."}
    meta = prev["decode"]
    fps, size = meta.get("fps") or 30.0, (meta.get("width"), meta.get("height"))
    shots = meta.get("shots") or [{"start_frame": 0, "end_frame": max(0, (meta.get("frames") or 1) - 1)}]
    wanted = sorted({f for sh in shots for f in court_registration.sample_frames(sh["start_frame"], sh["end_frame"], fps)})
    detectors = {name: court_detector(path) for name, path in models.items()}
    motion = motion_of(out)
    # one sequential pass: decode only the sampled frames, every model on each
    keypoints, cap, i, k = {name: {} for name in models}, cv2.VideoCapture(str(video)), 0, 0
    while k < len(wanted) and cap.grab():
        if i == wanted[k]:
            ok, frame = cap.retrieve()
            if ok:
                for name, detect in detectors.items():
                    keypoints[name][i] = detect(frame)
            k += 1
            if k % 10 == 0:
                tick(k / len(wanted))
        i += 1
    cap.release()
    empty = np.zeros((14, 3))
    registered = court_registration.pick({
        name: court_registration.register(shots, fps, size, lambda f, kp=kp: kp.get(f, empty), motion=motion)
        for name, kp in keypoints.items()})
    for k, shot in enumerate(registered):  # still shots: line evidence on the background plate decides
        if court_registration.still(motion, shot["start_frame"], shot["end_frame"], size):
            plate = court_lines.background_plate(video, shot["start_frame"], shot["end_frame"])
            if plate is not None:
                registered[k] = court_registration.with_line_evidence(shot, plate, fps, size)
    counts = {st: sum(r["status"] == st for r in registered) for st in ("ok", "needs_review", "failed")}
    res = {"status": "done", "models": {name: path.name for name, path in models.items()}, "shots": registered,
           "counts": counts}
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


def person_counts(weights: str, frames: list, imgsz: int) -> list[int]:
    """People per frame found by a detector (tests replace this function with a fake)."""
    from ultralytics import YOLO
    model = YOLO(weights)
    return [len(model(f, imgsz=imgsz, conf=PLAYER_CFG.conf, classes=[players.PERSON], verbose=False)[0].boxes) for f in frames]


def choose_player_detector(video: Path, n_frames: int, samples: int = 8) -> tuple[players.TrackerConfig, dict]:
    """The player-only detector unless it misses most people on this footage (vball.players.prefer_generalist)."""
    if not Path(GENERAL_PLAYER_MODEL).exists() or not Path(PLAYER_CFG.model).exists() or n_frames < 1:
        return PLAYER_CFG, {"model": Path(PLAYER_CFG.model).stem, "reason": "default"}
    cap, picks = cv2.VideoCapture(str(video)), []
    for f in np.linspace(0, n_frames - 1, samples).astype(int):
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(f))
        ok, frame = cap.read()
        if ok:
            picks.append(frame)
    cap.release()
    spec = person_counts(PLAYER_CFG.model, picks, PLAYER_CFG.imgsz)
    gen = person_counts(str(GENERAL_PLAYER_MODEL), picks, PLAYER_CFG.imgsz)
    info = {"player_only_median": float(np.median(spec)) if spec else 0.0, "general_median": float(np.median(gen)) if gen else 0.0}
    if spec and gen and players.prefer_generalist(spec, gen):
        cfg = replace(PLAYER_CFG, model=str(GENERAL_PLAYER_MODEL))
        return cfg, {**info, "model": Path(cfg.model).stem,
                     "reason": "the player-only detector found too few people on this footage"}
    return PLAYER_CFG, {**info, "model": Path(PLAYER_CFG.model).stem, "reason": "player-only detector"}


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

    cfg, choice = choose_player_detector(video, n)
    df = players.track_frames(frames(), fps, cfg)
    size = (prev["decode"].get("width"), prev["decode"].get("height"))
    df = players.place_on_court(df, court_homography_at(prev.get("court"), size))
    df = players.roles(df, team_assignments(video, df))
    df.to_csv(out / "players.csv.gz", index=False, float_format="%.2f")
    placed = bool(df["placed"].any()) if len(df) else False
    others = df.loc[df["role"] == "other", "track_id"].nunique() if len(df) else 0
    res = {"status": "done", "model": cfg.label(), "detector_choice": choice,
           "tracks": int(df["track_id"].nunique()) if len(df) else 0,
           "rows": int(len(df)), "placed": placed, "other_tracks": int(others)}
    if not placed:
        res["message"] = "The court was not found, so everyone in view is kept and no court positions are given."
    return res


def action_detector():
    """frame -> rows of (action, conf, x1, y1, x2, y2). Tests replace this function with a fake."""
    from ultralytics import YOLO
    model = YOLO(str(ACTION_MODEL))

    def detect(frame):
        r = model(frame, imgsz=640, conf=actions.ActionConfig().min_conf, verbose=False)[0]
        return [(r.names[int(c)], float(p), *map(float, b))
                for c, p, b in zip(r.boxes.cls.tolist(), r.boxes.conf.tolist(), r.boxes.xyxy.tolist())]
    return detect


def person_classifier():
    """-> (class names, crops -> (n, classes) probabilities). Tests replace this function with a fake."""
    from ultralytics import YOLO
    model = YOLO(str(PERSON_MODEL))
    names = [model.names[i] for i in range(len(model.names))]

    def classify(crops):
        if not crops:
            return np.zeros((0, len(names)))
        return np.stack([r.probs.data.cpu().numpy() for r in model(crops, imgsz=224, verbose=False)])
    return names, classify


def ball_points(out: Path) -> dict[int, np.ndarray]:
    """frame -> detected ball (x, y) from the ball stage, for the actors' ball prior."""
    p = out / "ball.csv"
    if not p.exists():
        return {}
    df = pd.read_csv(p)
    df = df[df["visible"] > 0]
    return {int(f): np.array([x, y]) for f, x, y in zip(df["frame"], df["x"], df["y"])}


def digit_detector():
    """player crop -> rows of (digit, conf, x1, y1, x2, y2). Tests replace this function with a fake."""
    from ultralytics import YOLO
    model = YOLO(str(JERSEY_MODEL))

    def detect(crop):
        r = model(crop, imgsz=320, conf=0.25, verbose=False)[0]
        return [(int(r.names[int(c)]), float(p), *map(float, b))
                for c, p, b in zip(r.boxes.cls.tolist(), r.boxes.conf.tolist(), r.boxes.xyxy.tolist())]
    return detect


def player_crop(frame: np.ndarray, row) -> np.ndarray | None:
    """Upper 60% of a player box (numbers are on the back and chest), None when too small to read."""
    x1, y1, x2, y2 = (int(round(v)) for v in (row.x1, row.y1, row.x2, row.y2))
    h, w = frame.shape[:2]
    x1, x2, y1 = max(0, x1), min(w, x2), max(0, y1)
    y2 = min(h, y1 + int(0.6 * (y2 - y1)))
    if x2 - x1 < 16 or y2 - y1 < 24:
        return None
    return frame[y1:y2, x1:x2]


def actions_stage(video: Path, out: Path, prev: dict, tick) -> dict:
    """Action events per player track (vball.actions) and shirt numbers per track (vball.jersey). Block, receive, set
    and spike come from the per-player classifier weighted by the ball's position (vball.actors) when it is installed,
    serves from the action detector; without the classifier every action comes from the detector."""
    if not ACTION_MODEL.exists() and not PERSON_MODEL.exists():
        return {"status": "unavailable", "message": "The action model is not installed."}
    tracks_csv = out / "players.csv.gz"
    tracks = pd.read_csv(tracks_csv) if tracks_csv.exists() else pd.DataFrame(columns=players.COLUMNS)
    n, fps = prev["decode"].get("frames") or 0, prev["decode"].get("fps") or 30.0
    a_step, j_step = players.sample_every(fps, ACTION_FPS), players.sample_every(fps, JERSEY_FPS)
    detect = action_detector() if ACTION_MODEL.exists() else None
    person = person_classifier() if PERSON_MODEL.exists() else None
    read = digit_detector() if JERSEY_MODEL.exists() else None
    if "role" in tracks:
        tracks = tracks[tracks["role"] == "player"]  # officials and staff are not given actions or numbers
    seen = tracks[~tracks["interpolated"].astype(bool)] if len(tracks) else tracks
    by_frame = {f: g for f, g in seen.groupby("frame")} if read and len(seen) else {}
    boxes_at = {f: g for f, g in tracks.groupby("frame")} if person and len(tracks) else {}
    balls = ball_points(out) if person else {}
    rows, readings = [], {}
    cap, i = cv2.VideoCapture(str(video)), 0
    while True:
        wanted = i % a_step == 0 or (read is not None and i % j_step == 0 and i in by_frame)
        ok, frame = cap.read() if wanted else (cap.grab(), None)  # decode only the frames that are used
        if not ok:
            break
        if wanted:
            if i % a_step == 0:
                if detect is not None:
                    # with the classifier, the detector only contributes serves
                    rows.extend((i, *d) for d in detect(frame) if person is None or d[0] == "serve")
                if person is not None and i in boxes_at:
                    g = boxes_at[i]
                    boxes = g[["x1", "y1", "x2", "y2"]].to_numpy(float)
                    crops = [actors.person_crop(frame, b) for b in boxes]
                    keep = [k for k, c in enumerate(crops) if c is not None]
                    if keep:
                        names, classify = person
                        probs = classify([crops[k] for k in keep])
                        rows.extend(actors.classifier_rows(i, boxes[keep], probs, names, balls.get(i), BALL_PRIOR,
                                                           min_conf=actions.ActionConfig().min_conf))
            if read is not None and i % j_step == 0:
                for row in by_frame.get(i, pd.DataFrame()).itertuples():
                    crop = player_crop(frame, row)
                    if crop is not None:
                        readings.setdefault(int(row.track_id), []).append((i, jersey.reading(read(crop))))
        i += 1
        if n and i % 50 == 0:
            tick(i / n)
    cap.release()
    evs = actions.events(pd.DataFrame(rows, columns=actions.DETECTION_COLUMNS), tracks, a_step)
    numbers = {tid: jersey.vote([x for _, x in r]) for tid, r in readings.items()}
    # time-local numbers: a label follows a tracker identity switch instead of keeping the old number
    window = int(round(fps))  # +-1 s of readings
    segs = {tid: jersey.segments([f for f, _ in r], [x for _, x in r], window) for tid, r in readings.items()}
    data = {
        "events": [{"action": e.action, "track_id": e.track_id, "start_frame": e.start_frame, "end_frame": e.end_frame,
                    "start_s": round(e.start_frame / fps, 3), "end_s": round(e.end_frame / fps, 3),
                    "peak_conf": round(e.peak_conf, 3), "samples": e.samples} for e in evs],
        "numbers": {str(tid): {"number": v.number, "share": round(v.share, 3), "readings": v.readings}
                    for tid, v in sorted(numbers.items())},
        "segments": {str(tid): [list(s) for s in sg] for tid, sg in sorted(segs.items())},
        "reach": j_step,  # a segment covers its reading frames plus this many frames on each side
    }
    (out / "action_events.json").write_text(json.dumps(data))  # actions.json is the stage result
    by_action = {a: sum(e.action == a for e in evs) for a in actions.ACTIONS}
    res = {"status": "done", "models": {"actions": ACTION_MODEL.name if detect else None,
                                        "person": PERSON_MODEL.name if person else None,
                                        "digits": JERSEY_MODEL.name if read else None},
           "events": len(evs), "by_action": by_action,
           "numbered_tracks": sum(any(n is not None for _, _, n in sg) for sg in segs.values())}
    if read is None:
        res["message"] = "Shirt numbers are not read yet: the digit model is being retrained. Players are shown by tracking id."
    return res


def team_assignments(video: Path, df: pd.DataFrame, per_track: int = 10) -> dict:
    """vball.teams on torso colours of up to `per_track` detected (not interpolated) boxes per track."""
    seen = df[~df["interpolated"].astype(bool)] if len(df) else df
    if not len(seen):
        return {}
    picks = {}
    for tid, g in seen.groupby("track_id"):
        for r in g.iloc[np.linspace(0, len(g) - 1, min(per_track, len(g))).astype(int)].itertuples():
            picks.setdefault(int(r.frame), []).append((int(tid), (r.x1, r.y1, r.x2, r.y2)))
    hists: dict[int, list] = {}
    cap, i, last = cv2.VideoCapture(str(video)), 0, max(picks)
    while i <= last:
        ok, frame = cap.read() if i in picks else (cap.grab(), None)
        if not ok:
            break
        for tid, box in picks.get(i, []):
            crop = teams.torso_crop(frame, box)
            if crop is not None and crop.size:
                hists.setdefault(tid, []).append(teams.colour_hist(crop))
        i += 1
    cap.release()
    n_frames = df["frame"].nunique()
    coverage = (df.groupby("track_id")["frame"].nunique() / max(n_frames, 1)).to_dict()
    return teams.assign({t: np.array(h) for t, h in hists.items()}, coverage)


def ball_uv(out: Path, n_frames: int) -> np.ndarray:
    """(n_frames, 2) ball image positions, NaN where the ball was not detected."""
    import pandas as pd
    uv = np.full((n_frames, 2), np.nan)
    df = pd.read_csv(out / "ball.csv")
    df = df[(df["visible"] > 0) & (df["frame"] < n_frames)]
    uv[df["frame"].to_numpy(int)] = df[["x", "y"]].to_numpy(float)
    return uv


def flight_camera(court_result: dict, frame: int, size: tuple[int, int], motion, tries: int = 5):
    """(calibration, reason) for the camera at a frame: the court samples nearest the frame, their keypoints moved
    to it by the camera motion, the first that calibrates."""
    reason = "no court keypoints for calibration"
    for sample in court_registration.calibration_samples(court_result, frame, frame)[:tries]:
        kp = np.array(sample.get("keypoints") or [], float)
        if kp.shape != (14, 3):
            continue
        kp = court_registration.warp_keypoints(motion, sample["frame"], frame, kp)
        xy = np.where(kp[:, 2:3] >= 0.5, kp[:, :2], np.nan)  # unconfident keypoints count as unseen
        c = calibrate(xy, size)
        if c.status != "unusable":
            return c, None
        reason = c.reason
    return None, reason


def to_frame(motion, uv: np.ndarray, first: int, frames, ref: int) -> np.ndarray:
    """Ball positions uv (rows = frames from `first`) of the given frames moved to frame ref's image."""
    out = uv.copy()
    if motion is None:
        return out
    for f in frames:
        if np.isfinite(out[f]).all():
            out[f] = motion.warp(first + f, ref, out[f])[0]
    return out


def trajectory_stage(video: Path, out: Path, prev: dict, tick) -> dict:
    """3D flights in camera shots with a usable court, each flight with the camera of its own middle frame.

    With camera motion (decode stage), flights are found on the shot's ball track moved to the shot's first frame
    (a pan is not ball motion), and each flight is fitted in its middle frame's image: the ball positions and the
    nearest court sample's keypoints (net points included) are moved there and calibrated (vball.calibration).
    Writes flights.json: per flight its frames, ballistic parameters, quality and derived values."""
    meta = prev["decode"]
    n, fps, size = meta.get("frames") or 0, meta.get("fps") or 30.0, (meta.get("width"), meta.get("height"))
    court_result = prev.get("court") or {}
    shots = [s for s in court_result.get("shots", []) if s.get("status") in court_registration.USABLE and s.get("samples")]
    if not shots:
        (out / "flights.json").write_text("[]")
        return {"status": "done", "flights": 0, "calibrated_shots": 0,
                "message": "The camera could not be calibrated because the court was not found, so there are no 3D flights."}
    uv = ball_uv(out, n)
    motion = motion_of(out)
    # players placed on court, per frame: anchors for the touches (change constrain-3d-flights)
    placed = {}
    if (out / "players.csv.gz").exists():
        p = pd.read_csv(out / "players.csv.gz")
        if "placed" in p and p["placed"].any():
            p = p[p["placed"].astype(bool) & ((p["role"] == "player") if "role" in p else True)]
            placed = {int(f): g[["court_x", "court_y"]].to_numpy(float) for f, g in p.groupby("frame")}
    flights, unusable, rejected, uncalibrated, calibrated = [], [], [], 0, 0
    for k, shot in enumerate(shots):
        tick(k / len(shots))
        a, b = shot["start_frame"], shot["end_frame"]
        track = uv[a:b + 1]
        found, reason = trajectory.segment(to_frame(motion, track, a, range(len(track)), a)), None
        cams = {}
        for fl in found:
            ref = a + (fl.start + fl.end) // 2
            key = ref if motion is not None else None  # without motion the nearest sample is the camera of the shot
            if key not in cams:
                cams[key] = flight_camera(court_result, ref, size, motion)
            cal, why = cams[key]
            if cal is None:
                uncalibrated, reason = uncalibrated + 1, why
                continue
            rec = trajectory.reconstruct_flight(cal.camera, to_frame(motion, track, a, range(fl.start, fl.end + 1), ref),
                                                fl, fps, rejected=rejected, players_at=lambda f, a=a: placed.get(a + f))
            if rec is None:
                continue
            f = rec["fit"]
            flights.append({"start_frame": a + f.start, "end_frame": a + f.end, "p0": f.p0.tolist(), "v0": f.v0.tolist(),
                            "fit_px": f.fit_px, "depth_sd_m": f.depth_sd_m, "quality": f.quality, "reasons": f.reasons,
                            "derived": rec["derived"], "calibration": cal.status, "dropped": f.dropped,
                            "anchors": f.anchors, "camera_frame": ref})
        if any(c for c, _ in cams.values()):
            calibrated += 1
        elif found:
            unusable.append(reason)
    (out / "flights.json").write_text(json.dumps(flights))
    res = {"status": "done", "flights": len(flights), "calibrated_shots": calibrated,
           "low_quality": sum(f["quality"] == "low" for f in flights), "rejected": len(rejected),
           "anchored": sum(bool(f["anchors"]) for f in flights), "uncalibrated": uncalibrated,
           "motion": motion is not None}
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


def rally_cues(video: Path, tick):
    """Cues at 5 Hz (vball.rally_cues). Tests replace this function with a fake."""
    from vball.rally_cues import cues
    df, _, _ = cues(video, tick=tick)
    return df


def rallies(video: Path, out: Path, prev: dict, tick) -> dict:
    """Rallies (start, end, confidence) from the system's cues with the trained rally model (docs/results/rallies.md).
    Winners stay a user decision until landing calls exist; the worker writes the rallies to the database."""
    if not RALLY_MODEL.exists():
        return {"status": "unavailable", "message": "The rally model is not installed."}
    cues = rally_cues(video, tick)
    why = vrallies.outside_training(cues) if cues is not None else None
    if why:
        return {"status": "unavailable",
                "message": f"Rallies cannot be told on this footage: {why}. The rally model was trained on broadcast "
                           "views with the court in view."}
    found = vrallies.detect(vrallies.load_model(RALLY_MODEL), cues)
    rows = [{"start_s": round(a, 2), "end_s": round(b, 2), "confidence": round(c, 3)} for a, b, c in found]
    res = {"status": "done", "model": RALLY_MODEL.name, "count": len(rows), "rallies": rows}
    if not rows:
        res["message"] = "No rally found: the court, players and ball never looked like play."
    return res


FUNCS = {"decode": decode, "court": court, "ball": ball_stage, "players": players_stage, "actions": actions_stage,
         "trajectory": trajectory_stage, "events": events, "rallies": rallies}
# players -4: the general detector where the player-only one misses players
VERSIONS = {"decode": "2", "court": "5", "ball": f"{BALL_MODEL}-1", "players": f"{PLAYER_CFG.label()}-4",
            "actions": "3",  # 3: per-player classifier + ball prior
            "trajectory": "4", "events": "0.3", "rallies": "1"}  # rallies 1: detected from cues


def stage_file(results: Path, stage: str) -> Path:
    return results / f"{stage}.json"


def load_stage(results: Path, stage: str) -> dict | None:
    f = stage_file(results, stage)
    return json.loads(f.read_text()) if f.exists() else None


def corrected_court(court: dict | None, decode: dict | None, corrections: list[dict], results: Path | None = None) -> dict | None:
    """The court stage result with the user's corrections overlaid (never written to court.json). With the results
    folder, a correction follows the camera motion through its shot."""
    if not corrections or not court or court.get("status") != "done" or not decode:
        return court
    motion = motion_of(results) if results is not None else None
    return court_registration.apply_corrections(court, corrections, (decode["width"], decode["height"]),
                                                motion=motion, fps=decode.get("fps"))


def run(video: Path, results: Path, from_stage: str = "decode",
        on_progress: Callable[[str, float], None] = lambda stage, p: None,
        court_corrections: Callable[[], list[dict]] | None = None) -> dict:
    """Run the pipeline; returns {stage: result}. Raises on the first failing stage. Court corrections are read
    (court_corrections()) when the court stage is reached and overlaid on the court result later stages see, so
    a correction saved while a job waits or decodes is still applied."""
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
        if stage == "court" and court_corrections is not None:
            cached = corrected_court(cached, out.get("decode"), court_corrections(), results)
        out[stage] = cached
        done_weight += WEIGHTS[stage]
        on_progress(stage, done_weight)
    return out
