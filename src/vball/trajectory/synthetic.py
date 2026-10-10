"""Synthetic rallies through a known camera, for tests and for measuring the 3D fit.

A rally is a list of touch points (court metres) and flight durations; each flight between two
touches is the ballistic path that joins them in that time. The generator projects every frame
through the camera, then adds detection noise and occlusions.
"""
from dataclasses import dataclass

import numpy as np

from ..calibration import Camera
from . import G


@dataclass
class SyntheticRally:
    positions: np.ndarray  # (N, 3) true 3D centre per frame
    uv: np.ndarray         # (N, 2) detections, NaN where occluded
    touches: list[int]     # frame index of each touch (flight boundaries), first and last included
    fps: float


def rally(touch_points, durations, fps: float = 50.0):
    """True positions per frame and touch frames for flights joining consecutive touch points."""
    pts = [np.asarray(p, float) for p in touch_points]
    positions, touches = [], [0]
    for a, b, T in zip(pts, pts[1:], durations):
        n = int(round(T * fps))
        v0 = (b - a - 0.5 * G * T ** 2) / T
        t = np.arange(n) / fps
        positions.append(a + np.outer(t, v0) + 0.5 * np.outer(t * t, G))
        touches.append(touches[-1] + n)
    positions.append(pts[-1][None])
    return np.vstack(positions), touches


def render(cam: Camera, touch_points, durations, fps: float = 50.0, noise_px: float = 0.0,
           occluded=(), seed: int = 0) -> SyntheticRally:
    """Project a rally; `occluded` lists frame indices with no detection."""
    positions, touches = rally(touch_points, durations, fps)
    uv = cam.project(positions)
    uv = uv + np.random.default_rng(seed).normal(0, noise_px, uv.shape)
    uv[list(occluded)] = np.nan
    return SyntheticRally(positions, uv, touches, fps)


def corrupt(uv: np.ndarray, image_size: tuple[int, int], miss: float = 0.0, false: float = 0.0,
            noise_px: float = 0.0, burst: int = 4, seed: int = 0) -> np.ndarray:
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
        lost[a:a + max(1, int(rng.poisson(burst)))] = True
    lost[np.flatnonzero(lost)[target:]] = False  # trim the last burst to the exact share
    out[lost] = np.nan
    seen = np.flatnonzero(~np.isnan(out).any(axis=1))
    bad = rng.choice(seen, size=int(round(false * len(seen))), replace=False) if len(seen) else []
    out[bad] = rng.uniform([0, 0], image_size, (len(bad), 2))
    return out


def touch_players(touch_points, jitter_m: float = 0.3, last_is_floor: bool = True, seed: int = 0) -> list:
    """Court position (x, y) of the player at each touch, or None for the final floor contact: the touch's
    ground point plus a small offset (feet are not exactly under the ball)."""
    rng = np.random.default_rng(seed)
    out = [np.asarray(p, float)[:2] + rng.normal(0, jitter_m, 2) for p in touch_points]
    if last_is_floor:
        out[-1] = None
    return out
