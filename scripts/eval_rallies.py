"""Rally detection on the game-state dataset: a ball rule and a classifier on the system's cues, measured on held-out
matches.

Inputs: cues per match (`scripts/extract_rally_cues.py`, 5 samples per second) and the CVAT labels (serving-start ->
in-game-end per rally). Split by match (design of change add-rally-detection): train 2, 4, 8, 13; validation 3, 10;
test 6, 9. Methods:
  ball rule     P(play) = share of frames with a ball detection over the surrounding second
  classifier    gradient boosting on a window of cues around each sample (court, players, ball), trained on train
Segmentation thresholds (vball.rallies.RallyConfig) are chosen on validation by F1; test is reported once.

  python scripts/eval_rallies.py --cues <dir with <match>.csv and <match>.json> \
      --labels data/datasets/gamestate/labels [--out outputs/rallies]
"""
import argparse
import itertools
import json
from pathlib import Path

import numpy as np
import pandas as pd

from vball.rallies import RallyConfig, evaluate, match, read_cvat, segment

SPLIT = {"train": [2, 4, 8, 13], "val": [3, 10], "test": [6, 9]}
CUES = ["court_conf", "court_ok", "players", "player_motion", "ball_seen", "ball_speed"]
WINDOW_S = (1.0, 3.0)  # rolling statistics over these spans (centred)


def features(cues: pd.DataFrame, rate: float) -> pd.DataFrame:
    """Each cue plus its centred rolling mean and std over WINDOW_S: a sample is judged with its context."""
    out = cues[CUES].astype(float).copy()
    for w in WINDOW_S:
        n = max(1, int(round(w * rate)))
        roll = cues[CUES].astype(float).rolling(n, center=True, min_periods=1)
        out = out.join(roll.mean().add_suffix(f"_m{w:g}")).join(roll.std().fillna(0).add_suffix(f"_s{w:g}"))
    return out


def play_labels(times: np.ndarray, rallies_s: list[tuple[float, float]]) -> np.ndarray:
    y = np.zeros(len(times), int)
    for a, b in rallies_s:
        y[(times >= a) & (times <= b)] = 1
    return y


def load(cues_dir: Path, labels_dir: Path, matches: list[int]):
    """Per match: (times, cues DataFrame, labelled rallies in seconds)."""
    out = {}
    for m in matches:
        c = pd.read_csv(cues_dir / f"{m}.csv")
        f = json.loads((cues_dir / f"{m}.json").read_text())["fps"]
        rallies = [(a / f, b / f) for a, b in read_cvat(labels_dir / f"{m}.xml")]
        out[m] = (c["t"].to_numpy(), c, rallies)
    return out


def ball_rule(c: pd.DataFrame, rate: float) -> np.ndarray:
    return c["ball_seen"].rolling(max(1, int(round(rate))), center=True, min_periods=1).mean().to_numpy()


def choose_config(val: dict, probs: dict) -> RallyConfig:
    grid = {"p_on": [0.5, 0.6, 0.7], "p_off": [0.3, 0.4, 0.5], "min_rally_s": [2.0, 3.0, 4.0],
            "min_gap_s": [0.5, 1.0, 2.0], "smooth_s": [0.5, 1.0, 2.0]}
    best = None
    for vals in itertools.product(*grid.values()):
        cfg = RallyConfig(**dict(zip(grid, vals)))
        if cfg.p_off > cfg.p_on:
            continue
        det = {m: segment(val[m][0], probs[m], cfg) for m in val}
        tp = sum(evaluate(det[m], val[m][2])["matched"] for m in val)
        nd, ng = sum(len(det[m]) for m in val), sum(len(val[m][2]) for m in val)
        f1 = 2 * tp / max(nd + ng, 1)
        if best is None or f1 > best[0]:
            best = (f1, cfg)
    return best[1]


def report(name: str, data: dict, probs: dict, cfg: RallyConfig) -> dict:
    det = {m: segment(data[m][0], probs[m], cfg) for m in data}
    per = {m: evaluate(det[m], data[m][2]) for m in data}
    tp = sum(r["matched"] for r in per.values())
    nd, ng = sum(r["detected"] for r in per.values()), sum(r["labelled"] for r in per.values())
    p, r = tp / max(nd, 1), tp / max(ng, 1)
    pairs = [pr for m in data for pr in match(det[m], data[m][2])]
    starts = [abs(d[0] - g[0]) for d, g in pairs]
    ends = [abs(d[1] - g[1]) for d, g in pairs]
    res = {"precision": p, "recall": r, "f1": 2 * p * r / max(p + r, 1e-9), "matched": tp, "detected": nd, "labelled": ng,
           "start_err_median_s": float(np.median(starts)) if starts else None,
           "end_err_median_s": float(np.median(ends)) if ends else None,
           "within_1s": float(np.mean(np.array(starts + ends) <= 1.0)) if starts else None,
           "per_match": per, "config": cfg.__dict__}
    fmt = lambda v, spec: "n/a" if v is None else format(v, spec)  # noqa: E731
    print(f"{name:16s} P {p:.3f} R {r:.3f} F1 {res['f1']:.3f}  median start err {fmt(res['start_err_median_s'], '.2f')} s, "
          f"end err {fmt(res['end_err_median_s'], '.2f')} s, within 1 s {fmt(res['within_1s'], '.0%')}  ({tp}/{ng} rallies, {nd} detected)")
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cues", required=True)
    ap.add_argument("--labels", required=True)
    ap.add_argument("--rate", type=float, default=5.0)
    ap.add_argument("--out", default="outputs/rallies")
    args = ap.parse_args()
    data = {s: load(Path(args.cues), Path(args.labels), ms) for s, ms in SPLIT.items()}

    from sklearn.ensemble import HistGradientBoostingClassifier
    X = pd.concat([features(data["train"][m][1], args.rate) for m in data["train"]])
    y = np.concatenate([play_labels(data["train"][m][0], data["train"][m][2]) for m in data["train"]])
    clf = HistGradientBoostingClassifier(max_iter=300, learning_rate=0.05, random_state=0).fit(X, y)

    results = {}
    for name, prob_fn in (("ball rule", lambda c: ball_rule(c, args.rate)),
                          ("classifier", lambda c: clf.predict_proba(features(c, args.rate))[:, 1])):
        probs = {s: {m: prob_fn(data[s][m][1]) for m in data[s]} for s in ("val", "test")}
        cfg = choose_config(data["val"], probs["val"])
        results[name] = {"val": report(f"{name} val", data["val"], probs["val"], cfg),
                         "test": report(f"{name} test", data["test"], probs["test"], cfg)}
        acc = np.mean([((probs["test"][m] >= 0.5) == play_labels(data["test"][m][0], data["test"][m][2])).mean()
                       for m in data["test"]])
        results[name]["test_sample_accuracy"] = float(acc)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "results.json").write_text(json.dumps(results, indent=2, default=str))
    print("written", out / "results.json")


if __name__ == "__main__":
    main()
