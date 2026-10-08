import numpy as np
import pandas as pd

from vball.players import TrackerConfig, interpolate_tracks, sample_every, track_frames


def fake_step(script):
    """A detector + tracker that returns pre-scripted rows per call, and records calls."""
    calls = []

    def step(image):
        calls.append(int(image[0, 0]))
        return script.get(int(image[0, 0]), [])

    return step, calls


def frames(n):
    return [np.full((4, 4), i, np.uint8) for i in range(n)]  # pixel value = frame number


def test_sampling_rate():
    assert [sample_every(30, 10), sample_every(25, 10), sample_every(30, 30), sample_every(30, 0)] == [3, 2, 1, 1]


def test_detector_runs_on_sampled_frames_only():
    step, calls = fake_step({})
    track_frames(frames(10), src_fps=30, cfg=TrackerConfig(det_fps=10), step=step)
    assert calls == [0, 3, 6, 9]


def test_boxes_are_interpolated_between_samples_and_ids_kept():
    step, _ = fake_step({
        0: [(7, 0, 0, 10, 10, 0.9)],
        3: [(7, 30, 0, 40, 10, 0.6)],
    })
    df = track_frames(frames(4), src_fps=30, cfg=TrackerConfig(det_fps=10), step=step)
    assert df["frame"].tolist() == [0, 1, 2, 3]
    assert set(df["track_id"]) == {7}
    assert df["x1"].tolist() == [0, 10, 20, 30]
    assert df["interpolated"].tolist() == [False, True, True, False]
    assert df.loc[df["interpolated"], "conf"].eq(0.6).all()  # the weaker endpoint


def test_no_extrapolation_and_long_gaps_stay_empty():
    df = pd.DataFrame([
        (2, 1, 0, 0, 1, 1, 0.9, False),
        (4, 1, 2, 0, 3, 1, 0.9, False),
        (20, 1, 18, 0, 19, 1, 0.9, False),
    ], columns=["frame", "track_id", "x1", "y1", "x2", "y2", "conf", "interpolated"])
    out = interpolate_tracks(df, n_frames=30, max_gap=5)
    assert out["frame"].tolist() == [2, 3, 4, 20]  # nothing before 2 or after 20; 4 -> 20 too long


def test_every_frame_when_detecting_at_full_rate():
    step, calls = fake_step({1: [(3, 0, 0, 1, 1, 0.5)]})
    df = track_frames(frames(3), src_fps=30, cfg=TrackerConfig(det_fps=30), step=step)
    assert calls == [0, 1, 2]
    assert df["frame"].tolist() == [1] and not df["interpolated"].any()
