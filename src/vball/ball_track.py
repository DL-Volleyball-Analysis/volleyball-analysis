"""From ball candidates to one ball track: drop fixed objects, link over time, fill short gaps.

1. Fixed objects. Floor dashes, logos and scoreboard digits look like a ball to the detector but move only with
   the camera. The global camera shift between frames is estimated by phase correlation. A candidate is a fixed
   object when (a) its patch barely changes against the camera-aligned patches `motion_k` frames before and after it
   and (b) candidates keep appearing at the same camera-aligned spot in at least `fixed_frames` of the `fixed_window`
   frames around it. (a) alone is not enough: on broadcast clips fixed objects change 9-24 and the ball 40-85 grey
   levels, but on darker gym footage the ball in flight changes only 13-19.
2. Linking. Viterbi over each frame's candidates plus a "no ball" state: cost = (1 - score) per detection,
   `miss_cost` per frame without one, and a motion term (step / (max_step x frames since the last
   detection))^2, infinite beyond 1. The best path is the track: one candidate per frame, or none.
3. Gap filling. Gaps of at most `max_gap` frames between detections are filled with a quadratic fitted to the
   detections on both sides (the ball flies on a parabola in the image to first order).

    track(frames, cands) -> DataFrame[frame, visible, x, y, radius]  (same columns as vball.ball.track)
"""
from dataclasses import dataclass

import cv2
import numpy as np
import pandas as pd

from .ball_detect import Candidate


@dataclass(frozen=True)
class TrackConfig:
    motion_k: int = 3          # frames before and after used for the fixed-object check
    motion_r: int = 8          # half size of the compared patch, pixels
    min_motion: float = 30.0   # mean absolute grey change below this: possibly a fixed object ...
    fixed_window: int = 10     # ... if candidates also sit at the same aligned spot in the frames around it
    fixed_frames: int = 6      # (at least this many of the +-fixed_window frames)
    fixed_radius: float = 6.0  # pixels
    max_step: float = 0.04     # largest ball step per frame, as a share of the frame width
    miss_cost: float = 0.6
    forget: int = 15           # after this many frames without a detection, any position may follow
    max_gap: int = 5           # gaps up to this many frames are filled
    fit_side: int = 4          # detections used on each side of a gap


def camera_shift(frames: list[np.ndarray], scale: float = 0.25) -> np.ndarray:
    """(n, 2) cumulative global image translation of each frame against the first, in pixels."""
    off = [np.zeros(2)]
    prev = None
    for f in frames:
        g = np.float32(cv2.resize(f, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA))
        if prev is not None:
            (dx, dy), _ = cv2.phaseCorrelate(prev, g)
            off.append(off[-1] + np.array([dx, dy]) / scale)
        prev = g
    return np.array(off)


def motion(frames: list[np.ndarray], shift: np.ndarray, i: int, x: float, y: float, k: int, r: int) -> float:
    """Smallest mean absolute change of the patch at (x, y) in frame i against frames i-k and i+k, aligned by
    the camera shift. inf when neither neighbour exists (no evidence either way)."""
    xi, yi = int(round(x)), int(round(y))
    a = frames[i][yi - r:yi + r + 1, xi - r:xi + r + 1].astype(np.float32)
    vals = []
    for j in (i - k, i + k):
        if not 0 <= j < len(frames):
            continue
        dx, dy = shift[j] - shift[i]
        xj, yj = int(round(x + dx)), int(round(y + dy))
        b = frames[j][yj - r:yj + r + 1, xj - r:xj + r + 1].astype(np.float32)
        if a.shape == b.shape == (2 * r + 1, 2 * r + 1):
            vals.append(float(np.abs(a - b).mean()))
    return min(vals) if vals else float("inf")


def drop_fixed(frames: list[np.ndarray], cands: list[list[Candidate]], cfg: TrackConfig = TrackConfig(),
               shift: np.ndarray | None = None) -> list[list[Candidate]]:
    shift = camera_shift(frames) if shift is None else shift
    aligned = [np.array([[c.x - shift[i][0], c.y - shift[i][1]] for c in cs]).reshape(-1, 2) for i, cs in enumerate(cands)]

    def recurs(i: int, p: np.ndarray) -> bool:
        lo, hi = max(0, i - cfg.fixed_window), min(len(cands), i + cfg.fixed_window + 1)
        hits = sum(1 for j in range(lo, hi) if j != i and len(aligned[j])
                   and np.min(np.hypot(*(aligned[j] - p).T)) <= cfg.fixed_radius)
        return hits >= cfg.fixed_frames

    return [[c for k, c in enumerate(cs)
             if not (motion(frames, shift, i, c.x, c.y, cfg.motion_k, cfg.motion_r) < cfg.min_motion
                     and recurs(i, aligned[i][k]))]
            for i, cs in enumerate(cands)]


def link(cands: list[list[Candidate]], width: int, cfg: TrackConfig = TrackConfig()) -> list[Candidate | None]:
    """The most likely ball per frame (None: no ball) under the costs in the module docstring."""
    n = len(cands)
    if n == 0:
        return []
    step = cfg.max_step * width
    states = [list(c) + [None] for c in cands]
    cost = [np.array([1 - s.score if s else cfg.miss_cost for s in states[0]])]
    last = [[s for s in states[0]]]           # last detection on the best path into each state
    gap = [[0 if s else 1 for s in states[0]]]
    back = []
    for i in range(1, n):
        ci, li, gi, bi = [], [], [], []
        for s in states[i]:
            best, arg = np.inf, 0
            for k in range(len(states[i - 1])):
                c = cost[-1][k]
                if not np.isfinite(c):
                    continue
                if s is None:
                    c += cfg.miss_cost
                else:
                    c += 1 - s.score
                    lp, g = last[-1][k], gap[-1][k] + 1
                    if lp is not None and g <= cfg.forget:
                        d = np.hypot(s.x - lp.x, s.y - lp.y) / (step * g)
                        c = c + d * d if d <= 1 else np.inf
                if c < best:
                    best, arg = c, k
            ci.append(best)
            bi.append(arg)
            li.append(last[-1][arg] if s is None else s)
            gi.append(gap[-1][arg] + 1 if s is None else 0)
        cost.append(np.array(ci))
        last.append(li)
        gap.append(gi)
        back.append(bi)
    j = int(np.argmin(cost[-1]))
    path = [states[-1][j]]
    for i in range(n - 2, -1, -1):
        j = back[i][j]
        path.append(states[i][j])
    return path[::-1]


def fill_gaps(xy: np.ndarray, cfg: TrackConfig = TrackConfig()) -> tuple[np.ndarray, np.ndarray]:
    """xy: (n, 2) with NaN where there is no ball. Returns (xy with short gaps filled, filled mask)."""
    xy = xy.copy()
    seen = ~np.isnan(xy[:, 0])
    filled = np.zeros(len(xy), bool)
    idx = np.flatnonzero(seen)
    for a, b in zip(idx[:-1], idx[1:]):
        if not 1 < b - a <= cfg.max_gap + 1:
            continue
        left, right = idx[idx <= a][-cfg.fit_side:], idx[idx >= b][:cfg.fit_side]
        t = np.concatenate([left, right])
        deg = 2 if len(t) >= 4 else 1
        for d in range(2):
            coef = np.polyfit(t, xy[t, d], deg)
            xy[a + 1:b, d] = np.polyval(coef, np.arange(a + 1, b))
        filled[a + 1:b] = True
    return xy, filled


def track(frames: list[np.ndarray], cands: list[list[Candidate]], cfg: TrackConfig = TrackConfig()) -> pd.DataFrame:
    """One ball track for a shot. frames: the frames the candidates came from (grey or BGR)."""
    frames = [f if f.ndim == 2 else cv2.cvtColor(f, cv2.COLOR_BGR2GRAY) for f in frames]
    width = frames[0].shape[1] if frames else 1
    path = link(drop_fixed(frames, cands, cfg), width, cfg)
    xy = np.array([[c.x, c.y] if c else [np.nan, np.nan] for c in path], float).reshape(-1, 2)
    xy, filled = fill_gaps(xy, cfg)
    visible = ~np.isnan(xy[:, 0])
    return pd.DataFrame({"frame": np.arange(len(xy)), "visible": visible.astype(int), "x": xy[:, 0], "y": xy[:, 1],
                         "radius": np.nan, "filled": filled.astype(int)})
