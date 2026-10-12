"""Decode: metadata, camera shots and camera motion."""
from pathlib import Path

import cv2
import numpy as np

from vball import camera_motion

from .. import config


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


def run(video: Path, out: Path, prev: dict, tick) -> dict:
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
            if last is not None and cv2.compareHist(last, h, cv2.HISTCMP_CORREL) < config.SHOT_CUT_CORRELATION:
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
        camera_motion.save(out / config.MOTION_FILE, steps, share)
    meta["frames"] = n  # container frame counts can be off; trust the decoded count
    shots = [{"start_frame": a, "end_frame": b - 1} for a, b in zip(cuts, cuts[1:] + [n])]
    return {"status": "done", **meta, "shots": shots, "motion": config.MOTION_FILE if n else None,
            "motion_share": round(float(np.median(share[1:])), 3) if n > 1 else None}
