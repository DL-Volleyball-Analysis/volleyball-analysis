"""Trajectory: 3D ball flights per camera shot."""
import json
from pathlib import Path

import numpy as np
import pandas as pd

from vball import court_registration, trajectory
from vball.calibration import calibrate

from .. import results


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


def run(video: Path, out: Path, prev: dict, tick) -> dict:
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
    uv = results.ball_uv(out, n)
    motion = results.motion_of(out)
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
        # one camera for the whole shot without motion or with a still camera (speed-up-analysis); else per flight
        moving = motion is not None and not court_registration.still(motion, a, b, size)
        for fl in found:
            ref = a + (fl.start + fl.end) // 2
            key = ref if moving else None
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
