"""Court: per-shot court registration, line evidence for still shots."""
from pathlib import Path

import cv2
import numpy as np

from vball import court_lines, court_registration

from .. import config, models, results


def run(video: Path, out: Path, prev: dict, tick) -> dict:
    """Per-shot court registration (vball.court_registration) with every installed court model, keeping the
    best model per shot; shots with a still camera are then decided by line evidence on their background plate
    (vball.court_lines)."""
    installed = {name: path for name, path in config.COURT_MODELS.items() if path.exists()}
    if not installed:
        return {"status": "unavailable", "message": "The court model has not been trained yet."}
    meta = prev["decode"]
    fps, size = meta.get("fps") or 30.0, (meta.get("width"), meta.get("height"))
    shots = meta.get("shots") or [{"start_frame": 0, "end_frame": max(0, (meta.get("frames") or 1) - 1)}]
    motion = results.motion_of(out)
    # still shots need fewer keypoint samples: their court does not move and line evidence decides (speed-up-analysis)
    rates = [court_registration.STILL_SAMPLE_FPS if court_registration.still(motion, sh["start_frame"], sh["end_frame"], size)
             else court_registration.SAMPLE_FPS for sh in shots]
    wanted = sorted({f for sh, r in zip(shots, rates) for f in court_registration.sample_frames(sh["start_frame"], sh["end_frame"], fps, r)})
    detectors = {name: models.court_detector(path) for name, path in installed.items()}
    # one sequential pass: decode only the sampled frames, every model on each
    keypoints, cap, i, k = {name: {} for name in installed}, cv2.VideoCapture(str(video)), 0, 0
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
        name: court_registration.register(shots, fps, size, lambda f, kp=kp: kp.get(f, empty), motion=motion, rates=rates)
        for name, kp in keypoints.items()})
    for k, shot in enumerate(registered):  # still shots: line evidence on the background plate decides
        if rates[k] == court_registration.STILL_SAMPLE_FPS:
            plate = court_lines.background_plate(video, shot["start_frame"], shot["end_frame"])
            if plate is not None:
                registered[k] = court_registration.with_line_evidence(shot, plate, fps, size)
    counts = {st: sum(r["status"] == st for r in registered) for st in ("ok", "needs_review", "failed")}
    res = {"status": "done", "models": {name: path.name for name, path in installed.items()}, "shots": registered,
           "counts": counts}
    if counts["ok"] < len(registered):
        res["message"] = (f"Court found in {counts['ok']} of {len(registered)} camera shots"
                          f" ({counts['needs_review']} to check, {counts['failed']} not found).")
    return res
