"""Rallies from a per-sample play probability, and their evaluation against labelled rallies.

    labels = read_cvat(xml)                          # [(start_frame, end_frame)] serving-start -> in-game-end
    rallies = segment(times, p_play, cfg)           # [(start_s, end_s, confidence)]
    m = evaluate(rallies, labelled_seconds)          # matched precision / recall, boundary errors

Segmentation: the probability is smoothed over `smooth_s`, a rally opens when it rises above `p_on` and closes
when it falls below `p_off` (hysteresis: a dip between the two thresholds does not split a rally); gaps shorter
than `min_gap_s` are merged and rallies shorter than `min_rally_s` dropped. A rally's confidence is its mean
probability. Evaluation matches detected and labelled rallies one to one by temporal IoU (at least `min_iou`,
greedy from the best pair).
"""
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

import numpy as np


@dataclass(frozen=True)
class RallyConfig:
    smooth_s: float = 1.0
    p_on: float = 0.6
    p_off: float = 0.4
    min_rally_s: float = 3.0
    min_gap_s: float = 1.0


def read_cvat(xml: str | Path) -> list[tuple[int, int]]:
    """Rallies (start frame, end frame) from CVAT tags: each serving-start opens a rally, the next in-game-end
    closes it. A start without an end before the next start is dropped (unfinished annotation)."""
    tags = []
    root = ET.parse(xml).getroot() if Path(str(xml)).exists() else ET.fromstring(xml)
    for image in root.iter("image"):
        for tag in image.iter("tag"):
            tags.append((int(image.get("id")), tag.get("label")))
    out, start = [], None
    for frame, label in sorted(tags):
        if label == "serving-start":
            start = frame
        elif label == "in-game-end" and start is not None:
            out.append((start, frame))
            start = None
    return out


def smooth(p: np.ndarray, n: int) -> np.ndarray:
    """Centred moving average over n samples (edges use the samples available)."""
    if n <= 1:
        return np.asarray(p, float)
    k = np.ones(n)
    num = np.convolve(p, k, mode="same")
    den = np.convolve(np.ones(len(p)), k, mode="same")
    return num / den


def segment(times: np.ndarray, p_play: np.ndarray, cfg: RallyConfig = RallyConfig()) -> list[tuple[float, float, float]]:
    """Rallies (start s, end s, confidence) from samples at `times` (seconds, increasing) with P(play)."""
    t, p = np.asarray(times, float), np.asarray(p_play, float)
    if len(t) == 0:
        return []
    dt = float(np.median(np.diff(t))) if len(t) > 1 else 1.0
    ps = smooth(p, max(1, int(round(cfg.smooth_s / dt))))
    runs, on, start = [], False, 0
    for i, v in enumerate(ps):
        if not on and v >= cfg.p_on:
            on, start = True, i
        elif on and v < cfg.p_off:
            runs.append([start, i - 1])
            on = False
    if on:
        runs.append([start, len(ps) - 1])
    merged: list[list[int]] = []
    for r in runs:
        if merged and t[r[0]] - t[merged[-1][1]] < cfg.min_gap_s:
            merged[-1][1] = r[1]
        else:
            merged.append(r)
    return [(float(t[a]), float(t[b]), float(ps[a:b + 1].mean())) for a, b in merged
            if t[b] - t[a] >= cfg.min_rally_s]


def iou(a: tuple[float, float], b: tuple[float, float]) -> float:
    inter = max(0.0, min(a[1], b[1]) - max(a[0], b[0]))
    union = max(a[1], b[1]) - min(a[0], b[0])
    return inter / union if union > 0 else 0.0


def match(detected, labelled, min_iou: float = 0.5) -> list[tuple]:
    """One-to-one (detected, labelled) pairs with temporal IoU >= min_iou, greedy from the best pair."""
    pairs = sorted(((iou(d[:2], g[:2]), i, j) for i, d in enumerate(detected) for j, g in enumerate(labelled)), reverse=True)
    used_d, used_g, out = set(), set(), []
    for v, i, j in pairs:
        if v < min_iou:
            break
        if i not in used_d and j not in used_g:
            used_d.add(i)
            used_g.add(j)
            out.append((detected[i], labelled[j]))
    return out


def evaluate(detected, labelled, min_iou: float = 0.5) -> dict:
    """detected, labelled: [(start s, end s, ...)]. Matched precision / recall, median boundary errors (s) and the
    share of matched boundaries within 1 s."""
    matches = match(detected, labelled, min_iou)
    ds = np.array([abs(d[0] - g[0]) for d, g in matches])
    de = np.array([abs(d[1] - g[1]) for d, g in matches])
    nd, ng = len(detected), len(labelled)
    p, r = len(matches) / max(nd, 1), len(matches) / max(ng, 1)
    return {"detected": nd, "labelled": ng, "matched": len(matches), "precision": p, "recall": r,
            "f1": 2 * p * r / max(p + r, 1e-9),
            "start_err_median_s": float(np.median(ds)) if len(ds) else None,
            "end_err_median_s": float(np.median(de)) if len(de) else None,
            "within_1s": float(np.mean(np.concatenate([ds, de]) <= 1.0)) if len(ds) else None}
