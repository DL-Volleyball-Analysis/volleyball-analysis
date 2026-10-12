"""Who sets, spikes, receives or blocks: the action model with and without the ball, on the Volleyball dataset.

Data: the Volleyball dataset (Ibrahim et al., CVPR 2016) with per-player boxes and action labels on 9 frames
around each clip's key frame (`annot_all.pkl` of the Kaggle copy), and the ball position in every frame
(Perez et al., Pattern Recognition 2022). Label mapping to our classes: setting -> set, digging -> receive,
spiking -> spike, blocking -> block; every other player (standing, moving, waiting, jumping, falling) has no
action. Serves are not labelled in this dataset, so `serve` predictions count as wrong.

Protocol: parameters are chosen on the validation matches and reported once on the test matches.
Methods (an ablation of vball.actors):
  key frame          the action model on the key frame only
  9 frames           each player's scores combined over the 9 frames (mean of the top_n)
  + ball (labelled)  each frame weighted by the distance from the player to the labelled ball
  + ball (detected)  the same with the ball from our tracker (--ball-preds, test matches only)
Metric: per player, F1 of each action class and their macro mean.

  python scripts/eval_actions_volleyball.py detect --videos <dir> --pkl annot_all.pkl --out dets.json
  python scripts/eval_actions_volleyball.py evaluate --pkl annot_all.pkl --ann <ball annotations> \
      --dets dets.json [--ball-preds <ball eval csv.gz>]
  python scripts/eval_actions_volleyball.py classifier --pkl annot_all.pkl --ann <ball annotations> \
      --probs person_action_test_probs.csv --k 2.0 --floor 0.6
The `classifier` command scores the per-player classifier (notebooks/train_person_actions.ipynb) on the same test
players and classes, alone and with the ball prior (k and floor as chosen on validation by `evaluate`).
"""
import itertools
import json
import pickle
from pathlib import Path

import numpy as np

from vball.actions import ACTIONS
from vball.actors import ActorConfig, combine, decide, player_scores

VAL_MATCHES = [0, 2, 8, 12, 17, 19, 24, 26, 27, 28, 30, 33, 46, 49, 51]
TEST_MATCHES = [4, 5, 9, 11, 14, 20, 21, 25, 29, 34, 35, 37, 43, 44, 45, 47]
LABEL_MAP = {"setting": "set", "digging": "receive", "spiking": "spike", "blocking": "block"}
SCORED = ["block", "receive", "set", "spike"]  # classes with labels here (no serve)


class _Box:
    def __setstate__(self, state):
        self.__dict__.update(state)


class _Unpickler(pickle.Unpickler):
    """annot_all.pkl holds `boxinfo.BoxInfo` objects; load them as plain attribute bags, nothing else."""

    def find_class(self, module, name):
        if module == "boxinfo":
            return _Box
        if module.split(".")[0] in ("builtins", "collections", "copyreg", "_codecs", "numpy"):
            return super().find_class(module, name)
        raise pickle.UnpicklingError(f"refusing {module}.{name}")


def load_annotations(path: Path) -> dict:
    """match -> clip -> {'category', 'frames': {frame: {player: (box, label)}}}"""
    raw = _Unpickler(open(path, "rb")).load()
    out = {}
    for m, clips in raw.items():
        for c, d in clips.items():
            frames = {int(f): {b.player_ID: (np.array(b.box, float), b.category) for b in bs}
                      for f, bs in d["frame_boxes_dct"].items()}
            out.setdefault(int(m), {})[int(c)] = {"category": d["category"], "frames": frames}
    return out


def detect(args):
    import cv2
    from ultralytics import YOLO
    model = YOLO(args.model)
    ann = load_annotations(Path(args.pkl))
    out = {}
    for m in VAL_MATCHES + TEST_MATCHES:
        for c, d in ann[m].items():
            for f in d["frames"]:
                img = cv2.imread(str(Path(args.videos) / str(m) / str(c) / f"{f}.jpg"))
                if img is None:
                    continue
                r = model(img, imgsz=640, conf=0.1, verbose=False)[0]
                out[f"{m}/{c}/{f}"] = [[int(a), round(float(p), 4), *[round(float(v), 1) for v in b]]
                                       for a, p, b in zip(r.boxes.cls.tolist(), r.boxes.conf.tolist(), r.boxes.xyxy.tolist())]
        print("match", m, "done", flush=True)
    Path(args.out).write_text(json.dumps(out))


def ball_at(ann_dir: Path, m: int, c: int) -> dict[int, np.ndarray | None]:
    """frame -> labelled ball (x, y) or None, for the 41 frames of a clip."""
    xy = np.loadtxt(ann_dir / str(m) / f"{c}.txt", ndmin=2)
    return {c - 20 + i: (None if p[0] == 0 and p[1] == 0 else p) for i, p in enumerate(xy)}


def detected_ball(path: Path) -> dict[tuple[int, int], dict[int, np.ndarray | None]]:
    """(match, clip) -> frame -> (x, y) or None, from a ball evaluation output (41 rows per clip, in order)."""
    import pandas as pd
    df = pd.read_csv(path)
    out = {}
    for (m, c), g in df.groupby(["match", "clip"], sort=False):
        c = int(c)
        out[(int(m), c)] = {c - 20 + i: (np.array([r.x, r.y]) if r.visible else None)
                            for i, r in enumerate(g.itertuples())}
    return out


def predictions(ann, dets, matches, cfg: ActorConfig, key_only: bool, balls=None):
    """[(true label or None, predicted label or None)] per labelled player at each clip's key frame."""
    pairs = []
    for m in matches:
        for c, d in ann[m].items():
            frames = {f: b for f, b in d["frames"].items() if not key_only or f == c}
            boxes = {f: {p: box for p, (box, _) in ps.items()} for f, ps in frames.items()}
            det = {f: np.array(dets.get(f"{m}/{c}/{f}", []), float).reshape(-1, 6) for f in frames}
            ball = None if balls is None else balls(m, c)
            s = decide(combine(player_scores(det, boxes, cfg, ball=ball), cfg.top_n), cfg.threshold)
            for p, (_, label) in d["frames"].get(c, {}).items():
                a = s.get(p)
                pairs.append((LABEL_MAP.get(label), None if a is None else ACTIONS[a]))
    return pairs


def f1s(pairs) -> dict:
    out = {}
    for a in SCORED:
        tp = sum(t == a and p == a for t, p in pairs)
        fp = sum(p == a and t != a for t, p in pairs)
        fn = sum(t == a and p != a for t, p in pairs)
        pr, rc = tp / max(tp + fp, 1), tp / max(tp + fn, 1)
        out[a] = {"precision": pr, "recall": rc, "f1": 2 * pr * rc / max(pr + rc, 1e-9), "support": tp + fn}
    serve_fp = sum(p == "serve" for _, p in pairs)
    out["macro_f1"] = float(np.mean([out[a]["f1"] for a in SCORED]))
    out["serve_predictions"] = serve_fp
    return out


def tune(ann, dets, key_only, balls=None, use_ball=False):
    """Best ActorConfig on the validation matches by macro F1."""
    grid = {"top_n": [1] if key_only else [1, 2, 3, 5, 9], "threshold": [0.2, 0.3, 0.4, 0.5, 0.6, 0.7],
            "k": [0.5, 1.0, 2.0] if use_ball else [1.0], "floor": [0.0, 0.2, 0.4, 0.6] if use_ball else [1.0]}
    best = None
    for vals in itertools.product(*grid.values()):
        cfg = ActorConfig(**dict(zip(grid, vals)))
        score = f1s(predictions(ann, dets, VAL_MATCHES, cfg, key_only, balls if use_ball else None))["macro_f1"]
        if best is None or score > best[0]:
            best = (score, cfg)
    return best


def evaluate(args):
    ann = load_annotations(Path(args.pkl))
    dets = json.loads(Path(args.dets).read_text())
    ann_dir = Path(args.ann)
    gt_ball = lambda m, c: ball_at(ann_dir, m, c)  # noqa: E731
    rows = []
    for name, key_only, use_ball in (("key frame", True, False), ("9 frames", False, False), ("+ ball (labelled)", False, True)):
        val, cfg = tune(ann, dets, key_only, gt_ball, use_ball)
        test = f1s(predictions(ann, dets, TEST_MATCHES, cfg, key_only, gt_ball if use_ball else None))
        rows.append((name, cfg, val, test))
    if args.ball_preds:
        det_ball = detected_ball(Path(args.ball_preds))
        cfg = rows[-1][1]  # the labelled-ball setting, chosen on validation; detected balls exist for test only
        test = f1s(predictions(ann, dets, TEST_MATCHES, cfg, False, lambda m, c: det_ball.get((m, c), {})))
        rows.append(("+ ball (detected)", cfg, float("nan"), test))
    print(f"{'method':20s} {'val macro F1':>12s} {'test macro F1':>13s}  " + "  ".join(f"{a:>7s}" for a in SCORED) + "  config")
    for name, cfg, val, test in rows:
        print(f"{name:20s} {val:12.3f} {test['macro_f1']:13.3f}  " + "  ".join(f"{test[a]['f1']:7.3f}" for a in SCORED)
              + f"  top_n={cfg.top_n} thr={cfg.threshold} k={cfg.k} floor={cfg.floor}")
    out = {name: {"config": cfg.__dict__, "val_macro_f1": val, "test": test} for name, cfg, val, test in rows}
    Path(args.out).write_text(json.dumps(out, indent=2))
    print("support (test players):", {a: rows[0][3][a]["support"] for a in SCORED})


def classifier(args):
    import pandas as pd

    from vball.actors import ball_prior
    ann = load_annotations(Path(args.pkl))
    df = pd.read_csv(args.probs)
    classes = [c for c in df.columns if c not in ("crop", "label")]
    probs = df[classes].to_numpy()
    is_action = np.array([c in LABEL_MAP for c in classes])
    cfg = ActorConfig(k=args.k, floor=args.floor)
    sources = {"labelled ball": lambda m, c: ball_at(Path(args.ann), m, c)}
    for path in args.ball_preds or []:  # detected balls from scripts/eval_ball_detection.py
        detected = detected_ball(Path(path))
        sources[f"detected ball ({Path(path).name.split('.')[0]})"] = lambda m, c, d=detected: d.get((m, c), {})
    variants = {"classifier": probs}
    for label, balls in sources.items():
        w = np.ones(len(df))
        for i, name in enumerate(df["crop"]):
            m, c, f, player = map(int, name.split("_"))
            w[i] = ball_prior(ann[m][c]["frames"][f][player][0], balls(m, c).get(f), cfg)
        weighted = probs.copy()
        weighted[:, is_action] *= w[:, None]
        variants[f"+ prior, {label}"] = weighted
    truth = df["label"].map(LABEL_MAP).tolist()
    out = {}
    for name, P in variants.items():
        pairs = [(t, LABEL_MAP.get(classes[k])) for t, k in zip(truth, P.argmax(axis=1))]
        out[name] = f1s(pairs)
        print(f"{name:40s} macro F1 {out[name]['macro_f1']:.3f}  " + "  ".join(
            f"{a} P {out[name][a]['precision']:.3f} R {out[name][a]['recall']:.3f} F1 {out[name][a]['f1']:.3f}" for a in SCORED))
    Path(args.out).write_text(json.dumps(out, indent=2))
