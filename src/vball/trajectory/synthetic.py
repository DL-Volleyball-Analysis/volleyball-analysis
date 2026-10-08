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
