"""Court error in metres from hand-labelled floor points (change verify-court-by-lines, task 3.1).

A person clicks known floor points on a still camera's background plate (`scripts/eval_fixed_court.py --make` writes
the plates and a labelling page). Each click is mapped to the court with the system's homography and compared with the
point's true court position. The court is symmetric, so which end is x = 0 is a convention of the fit: the error is
taken under the court symmetry (identity, end swap, side swap, both) that fits the clicks best.
"""

import numpy as np

from vball.court import LENGTH, WIDTH

# clicking order on the labelling page; court metres (x along the length, net at x = 9; y across)
POINTS = {
    "near end line, left corner": (0.0, 0.0),
    "near end line, right corner": (0.0, WIDTH),
    "near attack line, left end": (6.0, 0.0),
    "near attack line, right end": (6.0, WIDTH),
    "centre line under the net, left end": (9.0, 0.0),
    "centre line under the net, right end": (9.0, WIDTH),
}


def to_court(H: np.ndarray, px: np.ndarray) -> np.ndarray:
    """Image pixels (n, 2) -> court metres with the inverse of a court -> image homography."""
    p = np.column_stack([px, np.ones(len(px))]) @ np.linalg.inv(H).T
    return p[:, :2] / p[:, 2:3]


def symmetries(xy: np.ndarray) -> list[np.ndarray]:
    x, y = xy[:, 0], xy[:, 1]
    return [np.column_stack(c) for c in ((x, y), (LENGTH - x, y), (x, WIDTH - y), (LENGTH - x, WIDTH - y))]


def errors(H: np.ndarray, labels: dict[str, list[float] | None]) -> dict[str, float]:
    """{point name: error in metres} for the clicked points (None = not visible, skipped)."""
    names = [n for n in POINTS if labels.get(n) is not None]
    if not names:
        return {}
    measured = to_court(H, np.array([labels[n] for n in names], float))
    truth = np.array([POINTS[n] for n in names])
    best = min(symmetries(truth), key=lambda t: float(np.linalg.norm(measured - t, axis=1).sum()))
    return {n: float(e) for n, e in zip(names, np.linalg.norm(measured - best, axis=1))}


def summary(per_point: dict[str, float]) -> dict:
    e = np.array(list(per_point.values()))
    if not len(e):
        return {"points": 0}
    return {"points": len(e), "median_m": round(float(np.median(e)), 3), "max_m": round(float(e.max()), 3)}
