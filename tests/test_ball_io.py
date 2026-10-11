"""Ball detectors' decoding and I/O without the real ONNX models: fake sessions return chosen outputs."""
import json
from types import SimpleNamespace

import cv2
import numpy as np
import pandas as pd
import pytest

from vball import ball, ball_detect, metrics
from vball.ball_detect import Candidate, Ravel, VballNet


class FakeSession:
    """Stands in for onnxruntime.InferenceSession: records inputs, returns `make(inputs)`."""

    def __init__(self, make, input_name="clip", outputs=("heatmaps",)):
        self.make, self.calls = make, []
        self._in, self._out = input_name, outputs

    def get_inputs(self):
        return [SimpleNamespace(name=self._in)]

    def get_outputs(self):
        return [SimpleNamespace(name=n) for n in self._out]

    def run(self, _, feeds):
        x = feeds[self._in]
        self.calls.append(x.shape)
        return self.make(x)


def vballnet(monkeypatch, make, grid=None):
    monkeypatch.setattr(ball_detect, "_session", lambda path: FakeSession(make))
    return VballNet("unused.onnx", grid=grid)


def test_vballnet_maps_heatmap_peaks_to_image_pixels_and_pads_the_last_window(monkeypatch):
    def heat(x):  # a peak at heatmap (256, 144), the image centre, in every frame
        out = np.zeros((1, 9, 288, 512), np.float32)
        out[0, :, 143:146, 255:258] = 0.9
        return [out]
    det = vballnet(monkeypatch, heat)
    frames = [np.zeros((1080, 1920), np.uint8)] * 11  # one full window + a window of 2 (padded to 9)
    cands = det.candidates(frames)
    assert len(cands) == 11 and det.session.calls == [(1, 9, 288, 512)] * 2
    c = cands[10][0]
    assert abs(c.x - 960) < 4 and abs(c.y - 540) < 4 and abs(c.score - 0.9) < 1e-6


def test_vballnet_tiles_offset_candidates_and_merge_duplicates(monkeypatch):
    def heat(x):  # the same peak in the middle of every view
        out = np.zeros((1, 9, 288, 512), np.float32)
        out[0, :, 143:146, 255:258] = 0.8
        return [out]
    det = vballnet(monkeypatch, heat, grid=(2, 2))
    cands = det.candidates([np.zeros((1080, 1920), np.uint8)] * 9)
    assert len(det.session.calls) == 5  # whole frame + 4 tiles
    xs = sorted(round(c.x) for c in cands[0])
    assert len(cands[0]) == 5 and 960 in [round(x, -1) for x in xs]  # five different places, the centre once


def ravel(monkeypatch, tmp_path, grid_fn, channels=1):
    cfg = {"config": {"image_width": 640, "image_height": 360, "input_channels": channels}}
    (tmp_path / "m.json").write_text(json.dumps(cfg))
    monkeypatch.setattr(ball_detect, "_session",
                        lambda path: FakeSession(grid_fn, input_name="frames", outputs=("logits", "ball_grid")))
    return Ravel(tmp_path / "m.onnx", threshold=0.3, top_k=2)


def test_ravel_decodes_grid_peaks_with_offsets(monkeypatch, tmp_path):
    def grid(x):
        assert x.shape == (1, 9, 1, 360, 640)
        g = np.zeros((1, 9, 3, 36, 64), np.float32)
        g[0, :, 0, 18, 32] = 0.9                 # the ball: cell (row 18, col 32), offset (0.5, 0.5)
        g[0, :, 1:, 18, 32] = 0.5
        g[0, :, 0, 5, 5] = 0.4                   # a weaker second peak
        g[0, :, 0, 5, 6] = 0.35                  # not a local maximum: dropped
        g[0, :, 0, 30, 60] = 0.2                 # below threshold: dropped
        return [np.zeros(1), g]
    det = ravel(monkeypatch, tmp_path, grid)
    cands = det.candidates([np.zeros((1080, 1920, 3), np.uint8)] * 3)
    best, second = cands[0]
    assert len(cands) == 3 and len(cands[0]) == 2
    assert np.isclose(best.x, 32.5 / 64 * 1920) and np.isclose(best.y, 18.5 / 36 * 1080) and np.isclose(best.score, 0.9)
    assert np.isclose(second.score, 0.4)


def test_ravel_colour_input(monkeypatch, tmp_path):
    seen = []

    def grid(x):
        seen.append(x.shape)
        return [np.zeros(1), np.zeros((1, 9, 3, 45, 80), np.float32)]
    det = ravel(monkeypatch, tmp_path, grid, channels=3)
    assert det.candidates([np.zeros((720, 1280, 3), np.uint8)]) == [[]] and seen == [(1, 9, 3, 360, 640)]


def test_ball_load_reads_upstream_csv(tmp_path):
    p = tmp_path / "ball.csv"
    pd.DataFrame({"Frame": [0, 1], "Visibility": [1, 0], "X": [10, -1], "Y": [20, -1], "Radius": [5, 0]}).to_csv(p, index=False)
    df = ball.load(p)
    assert list(df.columns) == ["frame", "visible", "x", "y", "radius"]
    assert df["visible"].tolist() == [1, 0] and np.isnan(df.loc[1, "x"])


def test_track_refined_runs_detector_and_tracker(monkeypatch, tmp_path):
    path = tmp_path / "clip.mp4"
    w = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), 25, (320, 180))
    for _ in range(12):
        w.write(np.zeros((180, 320, 3), np.uint8))
    w.release()

    class Det:
        def candidates(self, frames):
            return [[Candidate(10.0 + 5 * i, 90.0, 0.9)] for i in range(len(frames))]
    monkeypatch.setattr(ball_detect, "load", lambda name: Det())
    monkeypatch.setattr("vball.ball_track.drop_fixed", lambda frames, cands, cfg=None, shift=None: cands)
    df = ball.track_refined(path, "ravel012")
    assert len(df) == 12 and df["visible"].all() and np.allclose(df["x"], 10 + 5 * np.arange(12))


def test_metrics():
    track = pd.DataFrame({"frame": range(5), "visible": [1, 1, 0, 1, 1], "x": [0, 1, np.nan, 300, 4.0], "y": [0.0] * 5})
    assert metrics.detection_rate(track) == 0.8
    # 300 -> 4 is a jump; 1 -> 300 spans a missed frame and is not compared
    assert metrics.jump_rate(track, frame_width=1000, jump_frac=0.08) == pytest.approx(100 * 1 / 4)
    labels = pd.DataFrame({"frame": range(5), "visible": [1, 1, 1, 0, 1], "x": [0, 50, 2, 0, 4.0], "y": [0.0] * 5})
    r = metrics.accuracy(track, labels, tol_px=4)
    # tp: frames 0, 4; frame 1 is 49 px away (fp and fn); frame 2 missed (fn); frame 3 a detection with no ball (fp)
    assert (r["precision"], r["recall"]) == (0.5, 0.5) and r["frames"] == 5
