"""Camera motion: the image-to-image homography between frames, for cameras that pan and zoom.

Frames are converted to grey at WIDTH px. A keyframe gets up to MAX_CORNERS Shi-Tomasi corners, and each new frame is
registered to the keyframe directly (pyramidal Lucas-Kanade starting from the previous keyframe -> frame mapping,
RANSAC homography), so errors do not pile up frame by frame while the keyframe holds. When fewer than MIN_INLIERS of
the corners agree (players or crowd dominate, a large pan, a cut), the previous frame becomes the keyframe. Chaining
frame-to-frame estimates instead drifted on a still camera (change follow-camera-motion, design).

`steps[t]` maps frame t - 1 to frame t in full resolution pixels (steps[0] is the identity; a frame without an
estimate gets the identity and share 0). The mapping is exact for a camera that rotates and zooms about a fixed point,
and for points on one plane (the floor) under any camera motion.
"""
from collections.abc import Callable, Iterable
from pathlib import Path

import cv2
import numpy as np

WIDTH = 640
MAX_CORNERS = 600
MIN_INLIERS = 0.5
RANSAC_PX = 1.0  # at WIDTH


def _grey(frame: np.ndarray) -> tuple[np.ndarray, float]:
    s = WIDTH / frame.shape[1]
    g = cv2.resize(frame, (WIDTH, int(round(frame.shape[0] * s))), interpolation=cv2.INTER_AREA)
    return (cv2.cvtColor(g, cv2.COLOR_BGR2GRAY) if g.ndim == 3 else g), s


def _corners(g: np.ndarray) -> np.ndarray | None:
    return cv2.goodFeaturesToTrack(g, MAX_CORNERS, 0.005, 10)


def _register(a: np.ndarray, pts: np.ndarray | None, b: np.ndarray, guess: np.ndarray | None) -> tuple[np.ndarray | None, float]:
    """Homography image a -> image b from corners pts of a, and the share of corners that agree with it."""
    if pts is None or len(pts) < 12:
        return None, 0.0
    kw = {}
    nxt = None
    if guess is not None:
        nxt = cv2.perspectiveTransform(pts, guess).astype(np.float32)
        kw["flags"] = cv2.OPTFLOW_USE_INITIAL_FLOW
    p1, st, _ = cv2.calcOpticalFlowPyrLK(a, b, pts, nxt, winSize=(21, 21), maxLevel=3 if guess is not None else 4, **kw)
    st = st.ravel() == 1
    if st.sum() < 12:
        return None, 0.0
    H, inl = cv2.findHomography(pts[st], p1[st], cv2.RANSAC, RANSAC_PX)
    if H is None:
        return None, 0.0
    return H, float(inl.sum()) / len(pts)


def estimate(frames: Iterable[np.ndarray], tick: Callable[[int], None] = lambda i: None) -> tuple[np.ndarray, np.ndarray]:
    """(steps (n, 3, 3), inlier share (n,)) for a sequence of BGR or grey frames."""
    steps, share = [np.eye(3)], [1.0]
    key = pts = prev = None
    key_to_prev = np.eye(3)
    for i, frame in enumerate(frames):
        g, s = _grey(frame)
        if prev is None:
            key, pts, prev = g, _corners(g), g
            continue
        S = np.diag([s, s, 1.0])
        H, q = _register(key, pts, g, key_to_prev)
        if H is not None and q >= MIN_INLIERS:
            step = H @ np.linalg.inv(key_to_prev)
            key_to_prev = H
        else:  # new keyframe: the previous frame
            key, pts = prev, _corners(prev)
            H, q = _register(key, pts, g, None)
            step = key_to_prev = H if H is not None else np.eye(3)
        steps.append(np.linalg.inv(S) @ step @ S)
        share.append(q)
        prev = g
        tick(i)
    return np.array(steps), np.array(share)


class Motion:
    """Steps plus their running product, so the mapping between any two frames costs two matrix products."""

    def __init__(self, steps: np.ndarray):
        self.steps = np.asarray(steps, float)
        cum, T = np.empty_like(self.steps), np.eye(3)
        for t, step in enumerate(self.steps):
            T = step @ T
            T /= T[2, 2]
            cum[t] = T
        self.cum = cum  # frame 0 -> frame t

    def __len__(self) -> int:
        return len(self.steps)

    def between(self, a: int, b: int) -> np.ndarray:
        """Homography frame a -> frame b (either order); frames are clipped to the video."""
        n = len(self.steps) - 1
        a, b = min(max(a, 0), n), min(max(b, 0), n)
        if a == b:
            return np.eye(3)
        T = self.cum[b] @ np.linalg.inv(self.cum[a])
        return T / T[2, 2]

    def warp(self, a: int, b: int, pts) -> np.ndarray:
        """Image points (n x 2) at frame a moved to frame b."""
        p = np.asarray(pts, float).reshape(-1, 2)
        if a == b:
            return p.copy()
        return cv2.perspectiveTransform(p.reshape(-1, 1, 2), self.between(a, b)).reshape(-1, 2)


def save(path: Path, steps: np.ndarray, share: np.ndarray) -> None:
    np.savez_compressed(path, steps=steps.astype(np.float64), share=share.astype(np.float32))


def load(path: Path) -> Motion | None:
    """The motion saved for a video, or None when there is none."""
    path = Path(path)
    if not path.exists():
        return None
    with np.load(path) as d:
        return Motion(d["steps"])
