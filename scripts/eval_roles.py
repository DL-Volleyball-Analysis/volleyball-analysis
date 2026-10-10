"""How well the appearance-based role check (vball.teams) separates players from everyone else, on SportsMOT
volleyball validation.

SportsMOT labels only the players on court, so a predicted track that matches no labelled player (IoU >= 0.5 on
at least half of its boxes) is a non-player: referee, line judge, coach, bench, spectator. Per sequence the tracks'
torso colour histograms are clustered into two teams; tracks far from both are role `other`. No court mapping is
available here, so the on-court override for the libero cannot apply: this measures colour alone. The thresholds
(fit_min_coverage, outlier_mads) were chosen on these sequences, so the numbers are optimistic until confirmed on
the SportsMOT training sequences.

Reports the share of non-player tracks and boxes marked other (caught), of player tracks and boxes marked other
(lost), and the box precision before and after dropping `other` boxes.

  .venv/bin/python scripts/eval_roles.py [--tracks outputs/player_tracking/yolo26s_960_botsort_10fps/data]
"""
import argparse
from collections import Counter
from pathlib import Path

import cv2
import numpy as np
import pandas as pd

from vball.paths import DATASETS, OUTPUTS
from vball.teams import assign, colour_hist, torso_crop

COLS = ["frame", "id", "x", "y", "w", "h"]


def load(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, header=None).iloc[:, :6]
    df.columns = COLS
    return df


def iou(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """IoU of box a (x, y, w, h) against boxes b (N, 4)."""
    x1, y1 = np.maximum(a[0], b[:, 0]), np.maximum(a[1], b[:, 1])
    x2, y2 = np.minimum(a[0] + a[2], b[:, 0] + b[:, 2]), np.minimum(a[1] + a[3], b[:, 1] + b[:, 3])
    inter = np.clip(x2 - x1, 0, None) * np.clip(y2 - y1, 0, None)
    return inter / (a[2] * a[3] + b[:, 2] * b[:, 3] - inter)


def is_player(pred: pd.DataFrame, gt_by_frame: dict) -> pd.Series:
    """Per predicted box: does it overlap a labelled player (IoU >= 0.5)? Then per track: majority of its boxes."""
    hit = []
    for r in pred.itertuples():
        g = gt_by_frame.get(r.frame)
        hit.append(bool(g is not None and iou(np.array([r.x, r.y, r.w, r.h]), g).max() >= 0.5))
    pred = pred.assign(hit=hit)
    return pred.groupby("id")["hit"].mean() >= 0.5


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tracks", default=str(OUTPUTS / "player_tracking" / "yolo26s_960_botsort_10fps" / "data"))
    ap.add_argument("--samples", type=int, default=10, help="boxes per track for its colour")
    args = ap.parse_args()
    val = DATASETS / "sportsmot" / "val"
    tracks, boxes = Counter(), Counter()
    for seq in sorted(p.name for p in val.iterdir() if p.is_dir()):
        pred_path = Path(args.tracks) / f"{seq}.txt"
        if not pred_path.exists():
            continue
        pred, gt = load(pred_path), load(val / seq / "gt" / "gt.txt")
        gt_by_frame = {f: g[["x", "y", "w", "h"]].to_numpy(float) for f, g in gt.groupby("frame")}
        player = is_player(pred, gt_by_frame)
        hists = {}
        for tid, g in pred.groupby("id"):
            pick = g.iloc[np.linspace(0, len(g) - 1, min(args.samples, len(g))).astype(int)]
            hs = []
            for r in pick.itertuples():
                img = cv2.imread(str(val / seq / "img1" / f"{int(r.frame):06d}.jpg"))
                crop = torso_crop(img, (r.x, r.y, r.x + r.w, r.y + r.h)) if img is not None else None
                if crop is not None and crop.size:
                    hs.append(colour_hist(crop))
            hists[tid] = np.array(hs)
        cover = (pred.groupby("id")["frame"].nunique() / pred["frame"].nunique()).to_dict()
        roles = assign(hists, cover)
        n_box = pred.groupby("id").size()
        for tid in player.index:
            kind = "player" if player[tid] else "non-player"
            mark = "other" if roles[tid].other else "kept"
            tracks[(kind, mark)] += 1
            boxes[(kind, mark)] += int(n_box[tid])

    def share(c, kind):
        tot = c[(kind, "other")] + c[(kind, "kept")]
        return c[(kind, "other")] / max(tot, 1), tot

    for name, c in (("tracks", tracks), ("boxes", boxes)):
        caught, n_np = share(c, "non-player")
        lost, n_p = share(c, "player")
        print(f"{name}: non-players marked other {caught:.1%} of {n_np}; players marked other {lost:.1%} of {n_p}")
    before = boxes[("player", "kept")] + boxes[("player", "other")]
    before /= max(sum(boxes.values()), 1)
    after = boxes[("player", "kept")] / max(boxes[("player", "kept")] + boxes[("non-player", "kept")], 1)
    print(f"box precision (boxes on labelled players / all boxes): {before:.3f} -> {after:.3f} after dropping other")


if __name__ == "__main__":
    main()
