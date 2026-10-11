import importlib.util
from pathlib import Path

import cv2
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("tw", ROOT / "training" / "ball" / "train_wasb.py")
tw = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tw)


def fake_clips(root: Path):
    rows = []
    for src, n_clips in (("volleyball", 4), ("orel", 2)):
        for c in range(n_clips):
            folder = f"{src}/c{c}"
            (root / folder).mkdir(parents=True)
            for f in range(5):
                img = np.zeros((tw.H, tw.W, 3), np.uint8)
                cv2.circle(img, (100 + 10 * f, 50), 3, (255, 255, 255), -1)
                cv2.imwrite(str(root / folder / f"{f:05d}.jpg"), img)
            pd.DataFrame({"frame": range(5), "visible": [1, 1, 0, 1, 1], "x": [100, 110, -1, 130, 140],
                          "y": [50, 50, -1, 50, 50]}).to_csv(root / folder / "labels.csv", index=False)
            rows.append((src, "m", f"c{c}", "train", folder, 5, 4))
    pd.DataFrame(rows, columns=["source", "match", "clip", "split", "folder", "frames", "visible"]).to_csv(root / "manifest.csv", index=False)


def test_heatmap_peak_and_empty():
    h = tw.heatmap(100.0, 50.0, 2.5)
    assert h.shape == (tw.H, tw.W) and h[50, 100] == 1.0 and h[50, 110] < 0.01
    assert tw.heatmap(-1, -1, 2.5).max() == 0


def test_windows_validation_split_and_mix(tmp_path):
    fake_clips(tmp_path)
    clips = tw.load_clips(tmp_path, "train")
    tr, va = tw.split_val(clips, every=2)
    assert len(va) == 3 and len(tr) == 3  # every 2nd clip of each source
    w = tw.Windows(tr, 2.5, augment=False)
    assert len(w) == 3 * 3  # 5 frames -> 3 windows of 3 per clip
    x, y, xy = w[0]
    assert x.shape == (9, tw.H, tw.W) and y.shape == (3, tw.H, tw.W) and y[0][50, 100] == 1.0
    weights = tw.source_weights(w, {"volleyball": 0.5, "orel": 0.5})
    src = np.array([s for _, s, _ in w.items])
    assert np.isclose(weights[src == "orel"].sum(), 0.5) and np.isclose(weights.sum(), 1.0)


def test_flip_mirrors_labels(tmp_path, monkeypatch):
    fake_clips(tmp_path)
    w = tw.Windows(tw.load_clips(tmp_path, "train"), 2.5, augment=True)
    monkeypatch.setattr(tw.random, "random", lambda: 0.0)          # always flip
    monkeypatch.setattr(tw.random, "uniform", lambda a, b: (a + b) / 2)  # no colour change
    _, y, xy = w[0]
    assert xy[0, 0] == tw.W - 1 - 100 and xy[2, 0] == -1  # a missing ball stays missing
    assert y[0][50, tw.W - 1 - 100] == 1.0


def test_peaks_and_f1():
    hm = np.zeros((tw.H, tw.W), np.float32)
    hm[49:52, 99:102] = 0.9
    assert np.allclose(tw.peaks(hm), (100, 50)) and tw.peaks(np.zeros_like(hm)) is None
    preds = [(100, 50), None, (300, 50), (10, 10)]
    truths = np.array([[101, 50], [50, 50], [-1, -1], [100, 100]])
    # tp 1; fn: frame 1 missed, frame 3 far; fp: frame 2 (no ball), frame 3 far
    assert np.isclose(tw.f1_at(preds, truths, 2.0), 2 * 1 / (2 * 1 + 2 + 2))
