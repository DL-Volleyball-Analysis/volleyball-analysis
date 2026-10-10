"""Whole shirt numbers read by the digit model, on the test crops of the jersey digit set.

Each test crop's true number is its labelled digit boxes composed the same way as predictions (vball.jersey.reading,
left to right, side by side). Reports the share of crops read exactly, read wrong, and not read, overall and for
one- and two-digit numbers. Test crops come from matches whose teams appear in no training match.

  .venv/bin/python scripts/eval_jersey.py [--model models/jersey_digits_yolo26s.pt] [--data data/datasets/jersey_digits]
"""
import argparse
from collections import Counter
from pathlib import Path

import cv2
import numpy as np

from vball.jersey import reading
from vball.paths import DATASETS, MODELS


def true_number(label_text: str, w: int, h: int) -> str | None:
    rows = []
    for line in label_text.splitlines():
        p = line.split()
        if len(p) >= 5:
            c, x, y, bw, bh = int(p[0]), *map(float, p[1:5])
            rows.append((c, 1.0, (x - bw / 2) * w, (y - bh / 2) * h, (x + bw / 2) * w, (y + bh / 2) * h))
    return reading(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=str(MODELS / "jersey_digits_yolo26s.pt"))
    ap.add_argument("--data", default=str(DATASETS / "jersey_digits"))
    args = ap.parse_args()
    from ultralytics import YOLO
    model = YOLO(args.model)
    root = Path(args.data) / "test"
    out = Counter()
    by_len = {1: Counter(), 2: Counter()}
    confusions = Counter()
    for img_path in sorted((root / "images").iterdir()):
        img = cv2.imread(str(img_path))
        h, w = img.shape[:2]
        truth = true_number((root / "labels" / f"{img_path.stem}.txt").read_text(), w, h)
        if truth is None:
            continue
        r = model(img, imgsz=320, conf=0.25, verbose=False)[0]
        pred = reading(np.column_stack([r.boxes.cls.cpu().numpy(), r.boxes.conf.cpu().numpy(),
                                        r.boxes.xyxy.cpu().numpy()]) if len(r.boxes) else [])
        kind = "exact" if pred == truth else ("none" if pred is None else "wrong")
        out[kind] += 1
        by_len[min(len(truth), 2)][kind] += 1
        if kind == "wrong":
            confusions[(truth, pred)] += 1
    n = sum(out.values())
    print(f"test crops with a number: {n}")
    print(f"read exactly {out['exact'] / n:.1%}, wrong {out['wrong'] / n:.1%}, not read {out['none'] / n:.1%}")
    for k, c in by_len.items():
        m = sum(c.values())
        if m:
            print(f"  {k}-digit numbers ({m}): exact {c['exact'] / m:.1%}, wrong {c['wrong'] / m:.1%}, not read {c['none'] / m:.1%}")
    print("most common wrong readings (true -> read):", ", ".join(f"{t}->{p} x{k}" for (t, p), k in confusions.most_common(8)))


if __name__ == "__main__":
    main()
