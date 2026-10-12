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

court.json (stage result): {"status", "models", "shots": [{"start_frame", "end_frame", "status", "error", "model",
"samples": [{"frame", "corners_px": [[x, y] x 4], "error", "keypoints": [[x, y, conf] x 14]}]}]}. Corners
are in CORNER_IDS order (far left, far right, near right, near left) and already smoothed; keypoints are the
raw model output, kept for camera calibration (`vball.calibration`, which needs the net points).

User corrections (four known floor points at one frame of a shot: the corners, or for a camera behind an end
line the near half, CORRECTION_PRESETS) are stored apart from court.json and overlaid when the court is read
(`apply_corrections`): the shot becomes ok and `corrected`, with a sample whose 10 floor points follow from
the four (the floor is a plane) and whose 4 net points come from a camera calibrated on them, carried by the camera
motion to every sampled frame of the shot, so every later stage, 3D included, uses the correction as if the model had
found it, also when the camera pans.

Still shots (change verify-court-by-lines, `with_line_evidence`): the court fitted to the painted lines of the shot's
background plate (vball.court_lines) and the keypoint court are scored by line evidence on that plate; the better one
is used for the whole shot (`source`) and the status follows its line evidence (LINE_CONFIG), not the net check, which
passed courts squeezed into the near half of end-line views.

Camera motion (vball.camera_motion, change follow-camera-motion): smoothing moves each neighbouring sample to the
sample's frame before the median, and sampled frames without a court get the nearest detected court (at most
MAX_FILL_S away) moved to them, marked `filled` (they do not count as valid for the shot status).
"""

from collections.abc import Callable, Iterable

import cv2
import numpy as np

from .court_keypoints import (
    CORNER_IDS,
    K6Y7R_FLOOR,
    complete_floor,
    corners_from_homography,
    court_is_plausible,
    fit_homography,
    net_points_from_floor,
)

SAMPLE_FPS = 5.0
STILL_SAMPLE_FPS = 1.0  # still shots (change speed-up-analysis): the court does not move, line evidence decides
SMOOTH_WINDOW = 5
MAX_FILL_S = 5.0  # a sample without a court borrows the nearest detected one, moved by the camera motion
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


def smooth_corners(
    corners: list[np.ndarray], window: int = SMOOTH_WINDOW, frames: list[int] | None = None, motion=None
) -> list[np.ndarray]:
    """Running median per corner coordinate over `window` consecutive samples. The window stays centred:
    near the ends of a shot it shrinks on both sides (a one-sided window would pull a panning camera's
    first and last samples toward their neighbours). With camera motion (vball.camera_motion.Motion) and the
    samples' frames, each neighbour is first moved to the sample's frame, so a pan does not drag the median."""
    arr = np.stack(corners)
    out = []
    for i in range(len(arr)):
        half = min(window // 2, i, len(arr) - 1 - i)
        js = range(i - half, i + half + 1)
        if motion is None or frames is None:
            out.append(np.median(arr[i - half : i + half + 1], axis=0))
        else:
            out.append(np.median([motion.warp(frames[j], frames[i], arr[j]) for j in js], axis=0))
    return out


def fill_gaps(
    frames: list[int], valid: dict[int, dict], motion, fps: float, max_fill_s: float = MAX_FILL_S
) -> list[dict]:
    """Samples for sampled frames without a valid court: the nearest valid sample's corners and keypoints moved to
    the frame by the camera motion, when that sample is at most max_fill_s away. Marked filled."""
    have = sorted(valid)
    out = []
    if motion is None or not have:
        return out
    for f in frames:
        if f in valid:
            continue
        src = min(have, key=lambda g: abs(g - f))
        if abs(src - f) > max_fill_s * fps:
            continue
        v = valid[src]
        out.append(
            {
                "frame": f,
                "corners": motion.warp(src, f, v["corners"]),
                "error": v["error"],
                "keypoints": warp_keypoints(motion, src, f, v["keypoints"]),
                "filled": True,
            }
        )
    return out


def warp_keypoints(motion, a: int, b: int, keypoints) -> np.ndarray:
    """14 x (x, y, conf) keypoints at frame a moved to frame b (confidence kept). The net points move with the
    image homography too, exact for a camera that rotates and zooms."""
    kp = np.array(keypoints, float)
    if motion is not None and a != b:
        kp[:, :2] = motion.warp(a, b, kp[:, :2])
    return kp


def shot_status(
    n_samples: int, valid: int, errors: list[float], config: dict = CONFIG, consistency: float | None = None
) -> tuple[str, float | None]:
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
    return float(
        min(
            np.median(np.linalg.norm(cal.camera.project(k6y7r_points_3d(h)[net]) - kp[net, :2], axis=1))
            for h in (NET_TOP_MEN, NET_TOP_WOMEN)
        )
    )


def register_shot(
    start: int,
    end: int,
    fps: float,
    image_size: tuple[int, int],
    keypoints_at: Callable[[int], np.ndarray],
    config: dict = CONFIG,
    motion=None,
    rate: float = SAMPLE_FPS,
) -> dict:
    """Register one shot from samples at `rate` per second. keypoints_at(frame) -> 14 x (x, y, conf) for a sampled
    frame. With camera motion (vball.camera_motion.Motion), smoothing is motion-compensated and samples without a
    court are filled."""
    frames = sample_frames(start, end, fps, rate)
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
        smoothed = smooth_corners([v["corners"] for v in valid], frames=[v["frame"] for v in valid], motion=motion)
        for v, c in zip(valid, smoothed):
            v["corners"] = c
        found = valid + fill_gaps(frames, {v["frame"]: v for v in valid}, motion, fps)
        for v in sorted(found, key=lambda v: v["frame"]):
            x = {
                "frame": v["frame"],
                "corners_px": np.round(v["corners"], 2).tolist(),
                "error": round(v["error"], 5),
                "keypoints": np.round(v["keypoints"], 2).tolist(),
            }
            if v.get("filled"):
                x["filled"] = True
            samples.append(x)
    return {
        "start_frame": start,
        "end_frame": end,
        "status": status,
        "error": err,
        "consistency": None if consistency is None else round(consistency, 5),
        "samples": samples,
        "filled": sum(bool(x.get("filled")) for x in samples),
    }


def register(
    shots: Iterable[dict],
    fps: float,
    image_size: tuple[int, int],
    keypoints_at: Callable[[int], np.ndarray],
    config: dict = CONFIG,
    on_shot: Callable[[int], None] = lambda k: None,
    motion=None,
    rates: list[float] | None = None,
) -> list[dict]:
    """Register every shot; rates: samples per second per shot (default SAMPLE_FPS)."""
    out = []
    for k, s in enumerate(shots):
        rate = rates[k] if rates is not None else SAMPLE_FPS
        out.append(register_shot(s["start_frame"], s["end_frame"], fps, image_size, keypoints_at, config, motion, rate))
        on_shot(k)
    return out


LINE_CONFIG = {
    "still_px": 0.01,  # a shot is still when the camera motion moves the image centre less than this x width
    "min_good_lines": 5,  # status ok from line evidence: well supported court lines ...
    "min_support": 0.70,  # ... and the share of line samples on painted lines
}


def still(motion, start: int, end: int, image_size: tuple[int, int], config: dict = LINE_CONFIG) -> bool:
    """Whether the camera stays still over [start, end] (needs camera motion)."""
    if motion is None:
        return False
    w, h = image_size
    centre = np.array([[w / 2, h / 2]])
    frames = range(start, end + 1, max(1, (end - start) // 50 or 1))
    return max(float(np.linalg.norm(motion.warp(start, f, centre) - centre)) for f in frames) < config["still_px"] * w


def line_status(fit, config: dict = LINE_CONFIG) -> str:
    """ok / needs_review from line evidence (vball.court_lines.Fit)."""
    ok = fit.good_lines >= config["min_good_lines"] and fit.support >= config["min_support"]
    return "ok" if ok else "needs_review"


def keypoint_homography(shot: dict) -> np.ndarray | None:
    """The shot's keypoint court as one homography (median of its samples' corners), or None."""
    samples = [s for s in shot.get("samples", []) if not s.get("filled")]
    if not samples:
        return None
    corners = np.median([s["corners_px"] for s in samples], axis=0).astype(np.float32)
    return cv2.getPerspectiveTransform(COURT_CORNERS.astype(np.float32), corners)


def with_line_evidence(
    shot: dict, plate: np.ndarray, fps: float, image_size: tuple[int, int], config: dict = LINE_CONFIG
) -> dict:
    """A still shot decided by line evidence on its background plate (change verify-court-by-lines): the court fitted
    to the painted lines (vball.court_lines) and the keypoint court are scored on the same plate, the better one is
    used for every sampled frame, and the status follows its line evidence, not the net check. For a line fit the net
    points come from the net tape (`court_lines.focal_from_net`), so the camera can be calibrated for 3D in end-line
    views. Records `source` ("lines" or "keypoints") and the line evidence."""
    from . import court_lines

    found = court_lines.fit(plate)
    H_kp = keypoint_homography(shot)
    kp = court_lines.score_homography(plate, H_kp, dark=found.dark if found else False) if H_kp is not None else None
    best = max([f for f in (found, kp) if f is not None], key=lambda f: f.score, default=None)
    if best is None:
        return {**shot, "source": "keypoints", "lines": None}
    evidence = {
        "score": round(best.score, 1),
        "support": round(best.support, 3),
        "good_lines": best.good_lines,
        "dark": best.dark,
    }
    out = {
        **shot,
        "status": line_status(best, config),
        "lines": evidence,
        "source": "lines" if best is found else "keypoints",
    }
    if best is found:
        corners = corners_from_homography(best.H)
        frames = sample_frames(shot["start_frame"], shot["end_frame"], fps)
        net_px = None
        net = court_lines.focal_from_net(plate, best.H)  # the floor alone leaves a symmetric view's focal length open
        if net is not None:
            from .court_keypoints import K6Y7R_NET_IDS, k6y7r_points_3d

            net_px = court_lines.project(best.H, net[0], image_size, k6y7r_points_3d(net[1])[K6Y7R_NET_IDS])
            evidence.update(focal_px=round(net[0], 1), net_top_m=net[1], net_support=round(net[2], 3))
        try:
            base = corrected_sample(frames[0], corners, image_size, net_px=net_px)
        except ValueError:
            return {**shot, "source": "keypoints", "lines": evidence}
        out["samples"] = [{**base, "frame": f} for f in frames]
        out.update(error=0.0, consistency=None, filled=0)
    return out


STATUS_ORDER = ("ok", "needs_review", "failed")


def pick(candidates: dict[str, list[dict]]) -> list[dict]:
    """Per shot, the registration of the best model: status first (ok, needs review, failed), then the lower
    floor-net consistency, then the lower fit error (None counts as worst). candidates: model name -> the
    shots `register` returned with that model, all for the same shots in the same order. Each returned shot
    names its model."""
    names = list(candidates)
    if not names:
        return []

    def key(shot: dict):
        inf = float("inf")
        return (
            STATUS_ORDER.index(shot["status"]),
            inf if shot.get("consistency") is None else shot["consistency"],
            inf if shot.get("error") is None else shot["error"],
        )

    out = []
    for k in range(len(candidates[names[0]])):
        best = min(names, key=lambda n: key(candidates[n][k]))
        out.append({**candidates[best][k], "model": best})
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


def mapping_at(
    court: dict | None, frame: int, image_size: tuple[int, int] | None = None, statuses: tuple[str, ...] = USABLE
) -> np.ndarray | None:
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


CORRECTION_PRESETS = {
    "corners": CORNER_IDS,  # the four court corners: far left, far right, near right, near left (side views)
    "near_half": [2, 7, 9, 0],  # centre line left, right, end line right, left (camera behind an end line)
}


def corrected_sample(frame: int, points_px, image_size: tuple[int, int], ids=CORNER_IDS, net_px=None) -> dict:
    """A court sample from four user points on the floor (K6Y7R floor ids `ids`, default the corners): all 10
    floor points follow (the floor is a plane), the 4 net points come from a camera calibrated on them
    (confidence 0 when the view gives no focal length), or are `net_px` (4 x 2, ids 10-13) when given."""
    pts = np.asarray(points_px, float).reshape(4, 2)
    ids = [int(i) for i in ids]
    if len(set(ids)) != 4 or not all(0 <= i < 10 for i in ids):
        raise ValueError("four different floor points are needed")
    try:
        floor = complete_floor(pts, ids)
    except ValueError:
        raise ValueError("these points do not define the floor (three of them on one line?)") from None
    corners = floor[CORNER_IDS]
    if not court_is_plausible(corners, image_size):
        raise ValueError("these points do not give a plausible court: check their order")
    net = net_points_from_floor(floor, image_size) if net_px is None else np.asarray(net_px, float).reshape(4, 2)
    kp = np.zeros((14, 3))
    kp[:10, :2], kp[:10, 2] = floor, 1.0
    if net is not None:
        kp[10:, :2], kp[10:, 2] = net, 1.0
    return {"frame": int(frame), "corners_px": corners.tolist(), "error": 0.0, "keypoints": kp.tolist()}


def apply_corrections(
    court: dict | None, corrections: Iterable[dict], image_size: tuple[int, int], motion=None, fps: float | None = None
) -> dict | None:
    """The court with user corrections overlaid. corrections: {"shot", "frame", "points_px", "ids"} each (ids
    default to the corners); a correction replaces its shot's samples and status (ok, corrected). With camera
    motion and the video's fps, the corrected sample is moved to every sampled frame of the shot, so the court
    follows a panning camera; without, it holds for the whole shot. The stored court is not changed."""
    corrections = list(corrections)
    if court is None or not corrections:
        return court
    shots = [dict(s) for s in court.get("shots", [])]
    for c in corrections:
        k = int(c["shot"])
        if 0 <= k < len(shots):
            sample = corrected_sample(c["frame"], c["points_px"], image_size, c.get("ids") or CORNER_IDS)
            samples = [sample]
            if motion is not None and fps:
                sh = shots[k]
                frames = sorted(set(sample_frames(sh["start_frame"], sh["end_frame"], fps)) | {sample["frame"]})
                samples = [
                    {
                        "frame": f,
                        "corners_px": motion.warp(sample["frame"], f, sample["corners_px"]).tolist(),
                        "error": 0.0,
                        "keypoints": warp_keypoints(motion, sample["frame"], f, sample["keypoints"]).tolist(),
                    }
                    for f in frames
                ]
            shots[k].update(status="ok", corrected=True, error=0.0, consistency=None, samples=samples)
    return {**court, "shots": shots}
