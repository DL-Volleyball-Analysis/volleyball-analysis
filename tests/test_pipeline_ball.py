"""Ball stage picks its model by footage (change smooth-rally-playback, task 2.1)."""

import numpy as np
import pandas as pd
import pytest

from vball.pipeline import config, models, results
from vball.pipeline.stages import ball as ball_stage

DECODE = {"decode": {"width": 1920, "height": 1080, "frames": 100, "shots": [{"start_frame": 0, "end_frame": 99}]}}


class Motion:
    def __init__(self, px_per_frame: float):
        self.v = px_per_frame

    def warp(self, start, f, pts):
        return np.asarray(pts, float) + [self.v * (f - start), 0.0]


def track(*a, **k):
    return pd.DataFrame({"frame": [0, 1], "visible": [1, 0], "x": [5.0, np.nan], "y": [6.0, np.nan], "radius": [4, 4]})


@pytest.fixture
def stubs(monkeypatch, tmp_path):
    weights = tmp_path / "wasb_gym.onnx"
    weights.write_bytes(b"fake")  # outside models/: only has to exist
    monkeypatch.setattr(config, "GYM_BALL_MODEL", weights)
    calls = []
    monkeypatch.setattr(models, "gym_ball_track", lambda *a: calls.append("wasb") or track())
    monkeypatch.setattr(ball_stage.ball, "track", lambda *a, **k: calls.append("v4c") or track())
    return calls, weights


@pytest.mark.parametrize(("speed", "model"), [(0.0, "wasb_gym"), (5.0, "v4c")])
def test_still_camera_uses_the_gym_model(stubs, monkeypatch, tmp_path, speed, model):
    calls, _ = stubs
    monkeypatch.setattr(results, "motion_of", lambda out: Motion(speed))
    r = ball_stage.run(tmp_path / "v.mp4", tmp_path, DECODE, lambda p: None)
    assert r["model"] == model and calls == [model.split("_")[0]]
    assert (tmp_path / "ball.csv").exists() and r["detected"] == 1


def test_without_gym_weights_or_motion_vballnet_is_used(stubs, monkeypatch, tmp_path):
    calls, weights = stubs
    monkeypatch.setattr(results, "motion_of", lambda out: Motion(0.0))
    weights.unlink()
    r = ball_stage.run(tmp_path / "v.mp4", tmp_path, DECODE, lambda p: None)
    assert (r["model"], r["model_reason"]) == ("v4c", "gym ball model not installed")
    weights.write_bytes(b"fake")
    monkeypatch.setattr(results, "motion_of", lambda out: None)  # no camera motion: not known to be still
    assert ball_stage.run(tmp_path / "v.mp4", tmp_path, DECODE, lambda p: None)["model"] == "v4c"
