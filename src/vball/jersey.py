"""Shirt numbers from digit detections: compose digits into a reading per crop, vote per player track.

The digit model detects single digits 0-9 on a crop of the player (upper body). A reading joins the confident
digits left to right: at most two, and two only when they sit side by side (their boxes overlap vertically);
otherwise the more confident digit alone. Per track, the most frequent reading is the number when there are
at least `min_readings` readings and at least `min_share` of them agree; otherwise the track has no number and
is shown by its tracking id (never a guess).
"""
from collections import Counter
from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class JerseyConfig:
    min_conf: float = 0.5     # digits below this are ignored
    min_readings: int = 3     # a vote needs at least this many readings
    min_share: float = 0.6    # ... and this share agreeing


@dataclass
class Vote:
    number: int | None   # None: no clear vote
    share: float         # share of readings that agree with the most frequent one
    readings: int


def reading(digits: np.ndarray, cfg: JerseyConfig = JerseyConfig()) -> str | None:
    """digits: rows of (digit, conf, x1, y1, x2, y2) in one crop. The number read, as a string ('7', '10'),
    or None when no digit is confident enough."""
    d = np.asarray(digits, float).reshape(-1, 6)
    d = d[d[:, 1] >= cfg.min_conf]
    if not len(d):
        return None
    d = d[np.argsort(-d[:, 1])][:2]  # the two most confident
    if len(d) == 2:
        a, b = d
        overlap = min(a[5], b[5]) - max(a[3], b[3])
        if overlap <= 0.5 * min(a[5] - a[3], b[5] - b[3]):
            d = d[:1]  # not side by side: keep the more confident digit
    d = d[np.argsort(d[:, 2])]  # left to right
    return "".join(str(int(x)) for x in d[:, 0])


def vote(readings: list[str | None], cfg: JerseyConfig = JerseyConfig()) -> Vote:
    """The number of one track from its readings (None readings are ignored)."""
    r = [x for x in readings if x is not None]
    if not r:
        return Vote(None, 0.0, 0)
    best, n = Counter(r).most_common(1)[0]
    share = n / len(r)
    ok = len(r) >= cfg.min_readings and share >= cfg.min_share
    return Vote(int(best) if ok else None, share, len(r))


def label(track_id: int, number: int | None) -> str:
    """How a player is shown: '#7' with a number, 'ID 12' (the tracking id) without."""
    return f"#{number}" if number is not None else f"ID {track_id}"
