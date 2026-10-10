"""Teams and roles from appearance: who plays for which team, and who is not a player at all.

Per track, colour histograms of the torso (hue x saturation, plus value) from a few boxes are averaged; k-means
splits the long tracks into two teams. Only tracks seen in at least `fit_min_coverage` of the frames shape the team
centres: players stay in view, while spectators, bench and staff come and go (on SportsMOT volleyball val they
outnumber the players' tracks, and fitting on all tracks caught 3% of non-player boxes instead of 42%). A track far
from both team centres (beyond `outlier_mads` scaled median absolute
deviations of the within-team distances) is role `other`: referees, line judges, staff. When the two centres are
not clearly apart compared with the spread inside the teams, the split is not trusted and nobody is marked
`other` from colour alone. A track the court mapping places on the court most of the time stays a player whatever
its colour (the libero wears a different shirt).
"""
from dataclasses import dataclass

import cv2
import numpy as np

H_BINS, S_BINS, V_BINS = 12, 4, 4


@dataclass(frozen=True)
class TeamConfig:
    fit_min_coverage: float = 0.3  # tracks seen in at least this share of frames define the teams
    outlier_mads: float = 2.0     # distance to the nearest team centre, in scaled MADs above the median
    min_outlier_dist: float = 0.25  # ... and at least this (histograms sum to 1 per part)
    min_separation: float = 2.0   # centre distance / median within-team distance needed to trust the split
    min_tracks: int = 4           # fewer tracks: no clustering
    on_court_share: float = 0.5   # tracks on the court at least this often stay players
    court_margin_m: float = 0.5   # 'on the court' = inside the lines plus this margin


@dataclass
class Assignment:
    team: str | None  # "a" / "b", None when the split is not trusted or the track is other
    other: bool       # far from both teams by appearance


def torso_crop(frame: np.ndarray, box) -> np.ndarray | None:
    """The shirt: middle half of the box width, 15-50% of its height."""
    x1, y1, x2, y2 = (float(v) for v in box)
    w, h = x2 - x1, y2 - y1
    if w < 8 or h < 16:
        return None
    xa, xb = int(x1 + 0.25 * w), int(x2 - 0.25 * w)
    ya, yb = int(y1 + 0.15 * h), int(y1 + 0.5 * h)
    H, W = frame.shape[:2]
    xa, xb, ya, yb = max(0, xa), min(W, xb), max(0, ya), min(H, yb)
    return frame[ya:yb, xa:xb] if xb > xa and yb > ya else None


def colour_hist(crop: np.ndarray) -> np.ndarray:
    """Hue x saturation histogram and a value histogram, each summing to 1, concatenated."""
    hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
    hs = cv2.calcHist([hsv], [0, 1], None, [H_BINS, S_BINS], [0, 180, 0, 256]).ravel()
    v = cv2.calcHist([hsv], [2], None, [V_BINS], [0, 256]).ravel()
    return np.concatenate([hs / max(hs.sum(), 1), v / max(v.sum(), 1)])


def assign(track_hists: dict[int, np.ndarray], coverage: dict[int, float] | None = None,
           cfg: TeamConfig = TeamConfig()) -> dict[int, Assignment]:
    """track_hists: track id -> (n, d) histograms of its boxes; coverage: track id -> share of the frames it is
    seen in (None: every track shapes the teams). Team and other flag per track."""
    ids = [t for t, h in track_hists.items() if len(h)]
    fit_ids = [t for t in ids if coverage is None or coverage.get(t, 0.0) >= cfg.fit_min_coverage]
    if len(fit_ids) < cfg.min_tracks:
        return {t: Assignment(None, False) for t in track_hists}
    mean = {t: np.asarray(track_hists[t], np.float32).mean(axis=0) for t in ids}
    F = np.stack([mean[t] for t in fit_ids])
    crit = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 100, 1e-4)
    _, fit_labels, centres = cv2.kmeans(F, 2, None, crit, 10, cv2.KMEANS_PP_CENTERS)
    fit_labels = fit_labels.ravel()
    d = np.linalg.norm(F - centres[fit_labels], axis=1)  # spread inside the teams, from the defining tracks
    med = float(np.median(d))
    mad = 1.4826 * float(np.median(np.abs(d - med)))
    # the spread inside the teams, from the members closest to their centre (outliers inflate the median)
    inner = float(np.median(np.sort(d)[: max(2, len(d) // 2)]))
    separation = float(np.linalg.norm(centres[0] - centres[1])) / max(inner, 1e-6)
    if separation < cfg.min_separation:
        return {t: Assignment(None, False) for t in track_hists}
    limit = max(med + cfg.outlier_mads * mad, cfg.min_outlier_dist)
    # name teams by size so the larger cluster is "a" (stable between runs)
    order = np.argsort([-np.sum(fit_labels == k) for k in range(2)])
    name = {int(order[0]): "a", int(order[1]): "b"}
    out = {t: Assignment(None, False) for t in track_hists}
    for t in ids:
        dist = np.linalg.norm(centres - mean[t], axis=1)
        other = bool(dist.min() > limit)
        out[t] = Assignment(None if other else name[int(np.argmin(dist))], other)
    return out


def on_court_share(court_xy: np.ndarray, margin_m: float = TeamConfig().court_margin_m) -> float:
    """Share of a track's court positions inside the lines plus margin (NaN positions count as unknown)."""
    from .court import LENGTH, WIDTH
    p = np.asarray(court_xy, float).reshape(-1, 2)
    p = p[~np.isnan(p).any(axis=1)]
    if not len(p):
        return 0.0
    inside = (p[:, 0] >= -margin_m) & (p[:, 0] <= LENGTH + margin_m) & (p[:, 1] >= -margin_m) & (p[:, 1] <= WIDTH + margin_m)
    return float(inside.mean())
