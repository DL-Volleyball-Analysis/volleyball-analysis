"""Fixed-camera rally model: trained on score-bug labels of full matches, tested on other matches (change
label-rallies-from-score, task 2.2).

Labels (scripts/label_rallies.py) give the time each point appeared on the score bug, i.e. the end of a rally plus
the bug's delay, but no rally starts. Training samples are therefore labelled weakly: play in the PLAY_S seconds
before each rally end (bug time minus DELAY_S), no play from GAP_S after a rally end until GAP_S before the next
rally's play window; everything else is left out. The evaluation does not rest on those assumptions: a detected rally
counts when its end is followed by a point change on the bug within END_WINDOW_S (one to one, in time order), so
precision and recall are over points, and the delay from detected end to bug update is reported.

Cues: `vball.rally_cues.stage_cues` (scripts/extract_stage_cues.py). Classifier and segmentation as for broadcasts
(vball.rallies), segmentation thresholds chosen by leave-one-match-out on the training matches.

  .venv/bin/python scripts/train_fixed_rallies.py --test-cues outputs/rallies/fixed_cues \\
      --test-labels outputs/rallies/score_labels [--save models/rally_fixed_hgb.joblib]
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

from vball.rallies import RallyConfig, features, segment
from vball.rally_cues import STAGE_COLUMNS

RATE = 5.0
DELAY_S, PLAY_S, GAP_S = 4.0, 6.0, 2.0
END_WINDOW_S = (0.0, 12.0)  # a detected end counts if the bug changes this long after it
MIN_READ_SHARE = 0.5  # matches whose score bug was read in fewer frames leave most points unlabelled: not used
COLUMNS = [c for c in STAGE_COLUMNS if c != "t"]


def weak_labels(t: np.ndarray, changes: list[float]) -> np.ndarray:
    """1 play, 0 no play, -1 left out, per sample time."""
    y = np.full(len(t), -1)
    ends = sorted(c - DELAY_S for c in changes)
    for k, e in enumerate(ends):
        y[(t >= e - PLAY_S) & (t <= e)] = 1
        nxt = ends[k + 1] - PLAY_S - GAP_S if k + 1 < len(ends) else e + 30.0
        y[(t >= e + GAP_S) & (t <= nxt)] = 0
    return y


def match_ends(rallies: list[tuple[float, float, float]], changes: list[float], window=END_WINDOW_S) -> dict:
    """One-to-one matching of detected rally ends to bug changes in time order."""
    used, delays = set(), []
    for _, end, _ in sorted(rallies, key=lambda r: r[1]):
        cands = [k for k, c in enumerate(changes) if k not in used and window[0] <= c - end <= window[1]]
        if cands:
            k = min(cands, key=lambda k: changes[k])
            used.add(k)
            delays.append(changes[k] - end)
    tp = len(used)
    p = tp / len(rallies) if rallies else 0.0
    r = tp / len(changes) if changes else 0.0
    return {"detected": len(rallies), "points": len(changes), "matched": tp, "precision": round(p, 3),
            "recall": round(r, 3), "f1": round(2 * p * r / (p + r), 3) if p + r else 0.0,
            "median_delay_s": round(float(np.median(delays)), 2) if delays else None}


def load(cues_dir: Path, labels_dir: Path, min_read_share: float = MIN_READ_SHARE) -> dict:
    """name -> (cues, bug change times) for every match with cues and labels read well enough."""
    out = {}
    for f in sorted(cues_dir.glob("*.csv")):
        lab = labels_dir / f"{f.stem}.json"
        if not lab.exists():
            continue
        try:
            cues = pd.read_csv(f)
        except pd.errors.EmptyDataError:  # a match without an ok court has no cues (scripts/extract_stage_cues.py)
            continue
        if not len(cues):
            continue
        labels = json.loads(lab.read_text())
        if labels.get("read_share", 1.0) < min_read_share:
            continue
        out[f.stem] = (cues, [c["t"] for c in labels["changes"]])
    return out


def classifier():
    from sklearn.ensemble import HistGradientBoostingClassifier
    return HistGradientBoostingClassifier(max_iter=300, learning_rate=0.05, class_weight="balanced", random_state=0)


def fit(matches: dict):
    X, y = [], []
    for cues, changes in matches.values():
        lab = weak_labels(cues["t"].to_numpy(), changes)
        keep = lab >= 0
        X.append(features(cues, RATE, COLUMNS)[keep])
        y.append(lab[keep])
    return classifier().fit(pd.concat(X), np.concatenate(y))


def detect(model, cues: pd.DataFrame, cfg: RallyConfig):
    found = []
    for _, part in cues.groupby("shot"):  # rallies do not cross camera shots
        p = model.predict_proba(features(part, RATE, COLUMNS))[:, 1]
        found += segment(part["t"].to_numpy(), p, cfg)
    return found


def evaluate(model, matches: dict, cfg: RallyConfig) -> dict:
    per = {name: match_ends(detect(model, cues, cfg), changes) for name, (cues, changes) in matches.items()}
    tp = sum(v["matched"] for v in per.values())
    det = sum(v["detected"] for v in per.values())
    pts = sum(v["points"] for v in per.values())
    p, r = (tp / det if det else 0.0), (tp / pts if pts else 0.0)
    return {"precision": round(p, 3), "recall": round(r, 3), "f1": round(2 * p * r / (p + r), 3) if p + r else 0.0,
            "matched": tp, "detected": det, "points": pts, "per_match": per}


GRID = [RallyConfig(smooth_s=s, p_on=on, p_off=off, min_rally_s=m, min_gap_s=g)
        for s in (1.0, 2.0) for on, off in ((0.5, 0.5), (0.6, 0.4), (0.7, 0.5)) for m in (2.0, 3.0, 4.0) for g in (0.5, 1.5)]


def choose_config(train: dict) -> RallyConfig:
    """Segmentation thresholds by leave-one-match-out F1 on the training matches."""
    names = list(train)
    held = {n: fit({k: v for k, v in train.items() if k != n}) for n in names} if len(names) > 1 else None
    best, best_f1 = GRID[0], -1.0
    for cfg in GRID:
        if held is None:
            f1 = evaluate(fit(train), train, cfg)["f1"]
        else:
            tp = det = pts = 0
            for n in names:
                e = evaluate(held[n], {n: train[n]}, cfg)
                tp, det, pts = tp + e["matched"], det + e["detected"], pts + e["points"]
            p, r = (tp / det if det else 0.0), (tp / pts if pts else 0.0)
            f1 = 2 * p * r / (p + r) if p + r else 0.0
        if f1 > best_f1:
            best, best_f1 = cfg, f1
    return best
