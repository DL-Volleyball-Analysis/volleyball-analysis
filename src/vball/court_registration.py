"""Per-shot court registration: an image <-> court mapping for every frame of a video.

Within each camera shot the keypoint model runs on sampled frames (SAMPLE_FPS per second of video). Each
sample's floor keypoints give a homography (`court_keypoints.fit_homography`, with the geometric sanity
check); a sample without one is invalid. Per court corner, a running median over SMOOTH_WINDOW valid samples
removes single-sample jumps without crossing a shot boundary. A frame between samples gets its mapping from
the linearly interpolated corners (interpolating corners is well behaved under perspective; matrix entries
are not), so a panning camera is followed.

Shot status from CONFIG: failed (fewer than `min_valid_samples` valid samples: no mapping, never a guess),
needs_review (median error above `review_error`, fewer than `min_valid_share` of samples valid, or floor and
net keypoints that no single camera explains), ok.

The last check exists because a small homography error only means the floor points agree with each other.
Model v2 put the far end line on the net in views from behind an end line, squeezing the whole court into the
near half with a small error, while its net points were right. "Consistency" is the shot's median distance
between the predicted net points and where a camera calibrated on the floor points alone projects the net
(`vball.calibration`); the net points take no part in that fit, so the camera cannot bend toward them.

court.json (stage result): {"status", "model", "shots": [{"start_frame", "end_frame", "status", "error",
"samples": [{"frame", "corners_px": [[x, y] x 4], "error", "keypoints": [[x, y, conf] x 14]}]}]}. Corners
are in CORNER_IDS order (far left, far right, near right, near left) and already smoothed; keypoints are the
raw model output, kept for camera calibration (`vball.calibration`, which needs the net points).
"""
from typing import Callable, Iterable

import cv2
import numpy as np

from .court_keypoints import CORNER_IDS, K6Y7R_FLOOR, court_is_plausible, fit_homography

SAMPLE_FPS = 5.0
SMOOTH_WINDOW = 5
CONFIG = {
    "min_valid_samples": 2,
    "min_valid_share": 0.5,
    "review_consistency": 0.015,  # median net-point distance / image width (~29 px at 1080p): evaluation clips
                                  # 58-116 px when wrong by eye, 9-14 px when right
    "review_error": 0.005,  # median reprojection error / image diagonal (~11 px at 1080p); provisional, tuned
                            # on the evaluation's error distribution (task 3.4)
}

COURT_CORNERS = K6Y7R_FLOOR[CORNER_IDS].astype(np.float64)


def sample_frames(start: int, end: int, fps: float, rate: float = SAMPLE_FPS) -> list[int]:
    """Frames to analyse in [start, end] (inclusive): every fps / rate frames, plus the last frame."""
    step = max(1, int(round(fps / rate)))
    frames = list(range(start, end + 1, step))
    if frames[-1] != end:
        frames.append(end)
    return frames


def smooth_corners(corners: list[np.ndarray], window: int = SMOOTH_WINDOW) -> list[np.ndarray]:
    """Running median per corner coordinate over `window` consecutive samples. The window stays centred:
    near the ends of a shot it shrinks on both sides (a one-sided window would pull a panning camera's
    first and last samples toward their neighbours)."""
    arr = np.stack(corners)
    out = []
    for i in range(len(arr)):
        half = min(window // 2, i, len(arr) - 1 - i)
        out.append(np.median(arr[i - half:i + half + 1], axis=0))
    return out


def shot_status(n_samples: int, valid: int, errors: list[float], config: dict = CONFIG,
                consistency: float | None = None) -> tuple[str, float | None]:
    """consistency: the shot's median 14-point calibration error over the image width (None without net points)."""
    if valid < config["min_valid_samples"]:
        return "failed", None
    err = float(np.median(errors))
    if err > config["review_error"] or valid < config["min_valid_share"] * n_samples:
        return "needs_review", err
    if consistency is not None and consistency > config["review_consistency"]:
        return "needs_review", err
    return "ok", err


def consistency_px(keypoints: np.ndarray, image_size: tuple[int, int]) -> float | None:
    """How far (px, median) the confident net points are from where a camera calibrated on the floor points
    alone puts them; the lower of men's and women's net heights. None without a confident net point or a
    floor calibration. The net points take no part in the fit, so the camera cannot bend toward them."""
    from .calibration import calibrate
    from .court_keypoints import K6Y7R_NET_IDS, NET_TOP_MEN, NET_TOP_WOMEN, k6y7r_points_3d
    kp = np.asarray(keypoints, float)
    net = [i for i in K6Y7R_NET_IDS if kp[i, 2] >= 0.5]
    if not net:
        return None
    floor = np.where(kp[:, 2:3] >= 0.5, kp[:, :2], np.nan)
    floor[K6Y7R_NET_IDS] = np.nan
    cal = calibrate(floor, image_size, max_error_px=float("inf"), max_focal_sd=float("inf"))
    if cal.camera is None:
        return None
    return float(min(np.median(np.linalg.norm(cal.camera.project(k6y7r_points_3d(h)[net]) - kp[net, :2], axis=1))
                     for h in (NET_TOP_MEN, NET_TOP_WOMEN)))


def register_shot(start: int, end: int, fps: float, image_size: tuple[int, int],
                  keypoints_at: Callable[[int], np.ndarray], config: dict = CONFIG) -> dict:
    """Register one shot. keypoints_at(frame) -> 14 x (x, y, conf) for a sampled frame."""
    frames = sample_frames(start, end, fps)
    valid = []
    for f in frames:
        kp = np.asarray(keypoints_at(f), float)
        fit = fit_homography(kp, image_size)
        if fit is None:
            continue
        H, err = fit
        corners = cv2.perspectiveTransform(COURT_CORNERS.reshape(-1, 1, 2), H).reshape(-1, 2)
        valid.append({"frame": f, "corners": corners, "error": err, "keypoints": kp})
    checks = [c for c in (consistency_px(v["keypoints"], image_size) for v in valid) if c is not None]
    consistency = float(np.median(checks)) / image_size[0] if checks else None
    status, err = shot_status(len(frames), len(valid), [v["error"] for v in valid], config, consistency)
    samples = []
    if status != "failed":
        smoothed = smooth_corners([v["corners"] for v in valid])
        samples = [{"frame": v["frame"], "corners_px": np.round(c, 2).tolist(), "error": round(v["error"], 5),
                    "keypoints": np.round(v["keypoints"], 2).tolist()} for v, c in zip(valid, smoothed)]
    return {"start_frame": start, "end_frame": end, "status": status, "error": err,
            "consistency": None if consistency is None else round(consistency, 5), "samples": samples}


def register(shots: Iterable[dict], fps: float, image_size: tuple[int, int],
             keypoints_at: Callable[[int], np.ndarray], config: dict = CONFIG,
             on_shot: Callable[[int], None] = lambda k: None) -> list[dict]:
    out = []
    for k, s in enumerate(shots):
        out.append(register_shot(s["start_frame"], s["end_frame"], fps, image_size, keypoints_at, config))
        on_shot(k)
    return out


def _shot_of(court: dict | None, frame: int) -> dict | None:
    for s in (court or {}).get("shots", []):
        if s["start_frame"] <= frame <= s["end_frame"]:
            return s
    return None


USABLE = ("ok",)  # shots whose mapping later stages may use; needs_review is shown for review, not used


def corners_at(court: dict | None, frame: int, statuses: tuple[str, ...] = USABLE) -> np.ndarray | None:
    """Court corners (4 x 2 image pixels) at a frame, interpolated between the shot's samples; held
    constant before the first and after the last sample. None outside any shot and in shots whose status
    is not in `statuses` (by default only ok: a needs_review mapping may be wrong, and a wrong mapping
    would drop real players or misplace landings, which is worse than no mapping)."""
    shot = _shot_of(court, frame)
    if shot is None or shot["status"] not in statuses or not shot["samples"]:
        return None
    samples = shot["samples"]
    frames = [s["frame"] for s in samples]
    if frame <= frames[0]:
        return np.array(samples[0]["corners_px"], float)
    if frame >= frames[-1]:
        return np.array(samples[-1]["corners_px"], float)
    j = int(np.searchsorted(frames, frame))
    a, b = samples[j - 1], samples[j]
    t = (frame - a["frame"]) / (b["frame"] - a["frame"])
    return (1 - t) * np.array(a["corners_px"], float) + t * np.array(b["corners_px"], float)


def mapping_at(court: dict | None, frame: int, image_size: tuple[int, int] | None = None,
               statuses: tuple[str, ...] = USABLE) -> np.ndarray | None:
    """Court -> image homography at a frame (from the interpolated corners), or None."""
    c = corners_at(court, frame, statuses)
    if c is None:
        return None
    if image_size is not None and not court_is_plausible(c, image_size):
        return None
    return cv2.getPerspectiveTransform(COURT_CORNERS.astype(np.float32), c.astype(np.float32))


def calibration_samples(court: dict | None, start: int, end: int) -> list[dict]:
    """The samples (with raw keypoints) of the shot containing [start, end], nearest the middle first."""
    shot = _shot_of(court, (start + end) // 2)
    if shot is None or shot["status"] not in USABLE:
        return []
    mid = (start + end) / 2
    return sorted(shot["samples"], key=lambda s: abs(s["frame"] - mid))
