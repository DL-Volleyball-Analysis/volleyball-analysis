"""Label-free quality metrics for ball tracks.

Without ground truth we report two proxies:
  detection_rate  share of frames with a detection
  jump_rate       detections per 100 that jump more than `jump_frac` of the frame width
                  in one frame -- almost always a false positive (crowd, ad boards)
Use labelled frames (see `accuracy`) whenever they exist.
"""
import numpy as np
import pandas as pd


def detection_rate(track: pd.DataFrame) -> float:
    return float(track["visible"].mean())


def jump_rate(track: pd.DataFrame, frame_width: int, jump_frac: float = 0.08) -> float:
    step = np.hypot(track["x"].diff(), track["y"].diff())
    jumps = int((step > jump_frac * frame_width).sum())
    return 100.0 * jumps / max(1, int(track["visible"].sum()))


def accuracy(track: pd.DataFrame, labels: pd.DataFrame, tol_px: float) -> dict:
    """Precision / recall / F1 against labelled frames (columns: frame, visible, x, y)."""
    m = labels.merge(track, on="frame", suffixes=("_gt", "_pr"))
    gt, pr = m["visible_gt"] > 0, m["visible_pr"] > 0
    close = np.hypot(m["x_gt"] - m["x_pr"], m["y_gt"] - m["y_pr"]) <= tol_px
    tp = int((gt & pr & close).sum())
    fp = int((pr & ~(gt & close)).sum())
    fn = int((gt & ~(pr & close)).sum())
    p = tp / max(1, tp + fp)
    r = tp / max(1, tp + fn)
    return dict(precision=p, recall=r, f1=2 * p * r / max(1e-9, p + r), frames=len(m))
