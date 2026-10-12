"""Synthetic rallies through a known camera, for tests and for measuring the 3D fit.

A rally is a list of touch points (court metres) and flight durations; each flight between two
touches is the ballistic path that joins them in that time. The generator projects every frame
through the camera, then adds detection noise and occlusions.
"""

from dataclasses import dataclass

import numpy as np

from ..calibration import Camera, look_at
from . import BALL_RADIUS, Flight, G


@dataclass
class SyntheticRally:
    positions: np.ndarray  # (N, 3) true 3D centre per frame
    uv: np.ndarray  # (N, 2) detections, NaN where occluded
    touches: list[int]  # frame index of each touch (flight boundaries), first and last included
    fps: float


def rally(touch_points, durations, fps: float = 50.0):
    """True positions per frame and touch frames for flights joining consecutive touch points."""
    pts = [np.asarray(p, float) for p in touch_points]
    positions, touches = [], [0]
    for a, b, T in zip(pts, pts[1:], durations):
        n = int(round(T * fps))
        v0 = (b - a - 0.5 * G * T**2) / T
        t = np.arange(n) / fps
        positions.append(a + np.outer(t, v0) + 0.5 * np.outer(t * t, G))
        touches.append(touches[-1] + n)
    positions.append(pts[-1][None])
    return np.vstack(positions), touches


def render(
    cam: Camera, touch_points, durations, fps: float = 50.0, noise_px: float = 0.0, occluded=(), seed: int = 0
) -> SyntheticRally:
    """Project a rally; `occluded` lists frame indices with no detection."""
    positions, touches = rally(touch_points, durations, fps)
    uv = cam.project(positions)
    uv = uv + np.random.default_rng(seed).normal(0, noise_px, uv.shape)
    uv[list(occluded)] = np.nan
    return SyntheticRally(positions, uv, touches, fps)


def corrupt(
    uv: np.ndarray,
    image_size: tuple[int, int],
    miss: float = 0.0,
    false: float = 0.0,
    noise_px: float = 0.0,
    burst: int = 4,
    seed: int = 0,
) -> np.ndarray:
    """Detection errors as seen on real tracks: a `miss` share of frames lost in bursts of about `burst` frames
    (occlusions), a `false` share of the remaining detections replaced by uniform points in the image (other
    round things, heads), and Gaussian noise on the rest."""
    rng = np.random.default_rng(seed)
    out = np.asarray(uv, float).copy()
    n = len(out)
    seen = ~np.isnan(out).any(axis=1)
    out[seen] += rng.normal(0, noise_px, (int(seen.sum()), 2))
    target, lost = int(round(miss * n)), np.zeros(n, bool)
    while lost.sum() < target:
        a = int(rng.integers(0, n))
        lost[a : a + max(1, int(rng.poisson(burst)))] = True
    lost[np.flatnonzero(lost)[target:]] = False  # trim the last burst to the exact share
    out[lost] = np.nan
    visible = np.flatnonzero(~np.isnan(out).any(axis=1))  # frame indices still detected
    bad = (
        rng.choice(visible, size=int(round(false * len(visible))), replace=False) if len(visible) else np.zeros(0, int)
    )
    out[bad] = rng.uniform([0, 0], image_size, (len(bad), 2))
    return out


def touch_players(touch_points, jitter_m: float = 0.3, last_is_floor: bool = True, seed: int = 0) -> list:
    """Court position (x, y) of the player at each touch, or None for the final floor contact: the touch's
    ground point plus a small offset (feet are not exactly under the ball)."""
    rng = np.random.default_rng(seed)
    out: list[np.ndarray | None] = [np.asarray(p, float)[:2] + rng.normal(0, jitter_m, 2) for p in touch_points]
    if last_is_floor:
        out[-1] = None
    return out


# Reference scenario shared by the tests and scripts/eval_trajectory_synthetic.py: a 1080p side camera at 50 fps and
# serve -> receive -> set -> attack to the floor (court metres; side A is x < 9)
SIZE = (1920, 1080)
CAM = look_at([9.0, -14.0, 7.5], [9.0, 4.5, 0.5], 1600.0, SIZE)
FPS = 50.0
TOUCHES = [[-1.0, 7.0, 3.0], [14.5, 3.0, 0.8], [10.0, 5.5, 2.6], [10.5, 1.0, 3.2], [4.0, 6.0, BALL_RADIUS]]
DURATIONS = [1.3, 1.1, 0.9, 0.45]


def true_flights(r: SyntheticRally) -> list[Flight]:
    """The flights between consecutive touches of a synthetic rally."""
    return [Flight(a, b) for a, b in zip(r.touches, r.touches[1:])]
