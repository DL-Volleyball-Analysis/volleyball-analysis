"""How much of a tracker's error comes from people who are not players (referees, bench, crowd)?

SportsMOT labels only the players on court. This script keeps only the predicted tracks that match a
labelled player (IoU >= 0.5) in at least half of their frames, i.e. an ideal track-level on-court filter,
and re-evaluates. The result is an UPPER BOUND for what on-court filtering can give: it uses the labels
to decide which tracks to drop, which the real filter (court mapping) cannot.

  .venv/bin/python scripts/analyze_tracking_errors.py yolo26s_960_botsort_10fps
"""
import shutil
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from eval_player_tracking import GT_ROOT, RESULTS, evaluate, volleyball_val_seqs  # noqa: E402


def iou(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """IoU between boxes a (N, 4) and b (M, 4) in x, y, w, h."""
    ax2, ay2, bx2, by2 = a[:, 0] + a[:, 2], a[:, 1] + a[:, 3], b[:, 0] + b[:, 2], b[:, 1] + b[:, 3]
    iw = np.clip(np.minimum(ax2[:, None], bx2) - np.maximum(a[:, None, 0], b[:, 0]), 0, None)
    ih = np.clip(np.minimum(ay2[:, None], by2) - np.maximum(a[:, None, 1], b[:, 1]), 0, None)
    inter = iw * ih
    return inter / (a[:, 2:].prod(1)[:, None] + b[:, 2:].prod(1) - inter)


def player_tracks(pred: pd.DataFrame, gt: pd.DataFrame) -> set:
    matched = {}
    for frame, p in pred.groupby(0):
        g = gt[gt[0] == frame]
        hit = (iou(p[[2, 3, 4, 5]].to_numpy(float), g[[2, 3, 4, 5]].to_numpy(float)).max(1) >= 0.5) if len(g) else np.zeros(len(p), bool)
        for tid, h in zip(p[1], hit):
            n, k = matched.get(tid, (0, 0))
            matched[tid] = (n + 1, k + int(h))
    return {tid for tid, (n, k) in matched.items() if k >= 0.5 * n}


def main():
    label = sys.argv[1]
    out = f"{label}_oracle_players"
    seqs = volleyball_val_seqs()
    src, dst = RESULTS / label / "data", RESULTS / out / "data"
    shutil.rmtree(RESULTS / out, ignore_errors=True)
    dst.mkdir(parents=True)
    kept_boxes = total_boxes = kept_tracks = total_tracks = 0
    for seq in seqs:
        pred = pd.read_csv(src / f"{seq}.txt", header=None)
        gt = pd.read_csv(GT_ROOT / seq / "gt" / "gt.txt", header=None)
        keep = player_tracks(pred, gt)
        kept = pred[pred[1].isin(keep)]
        kept.to_csv(dst / f"{seq}.txt", header=False, index=False)
        kept_boxes, total_boxes = kept_boxes + len(kept), total_boxes + len(pred)
        kept_tracks, total_tracks = kept_tracks + len(keep), total_tracks + pred[1].nunique()
    print(f"{label}: kept {kept_tracks}/{total_tracks} tracks, {kept_boxes}/{total_boxes} boxes "
          f"(the rest never or rarely overlap a labelled player)")
    table = evaluate(seqs, out, None)
    print("UPPER BOUND with an ideal on-court filter (uses the labels):")
    print(table.loc[["COMBINED_SEQ"]].round(3).to_string())


if __name__ == "__main__":
    main()
