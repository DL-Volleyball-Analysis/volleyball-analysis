import numpy as np
import pytest
from vball.calibration import look_at
from vball.court_keypoints import k6y7r_points_3d

from test_api import run_worker_once, upload

CAM = look_at([9.0, -14.0, 7.5], [9.0, 4.5, 0.5], 300.0, (320, 180))  # the 320 x 180 test clip


def stage(client, vid, name):
    return {s["name"]: s for s in client.get(f"/videos/{vid}/stages").json()}[name]


@pytest.fixture
def installed(monkeypatch, tmp_path):
    import pipeline
    weights = tmp_path / "court_kpt.pt"
    weights.write_bytes(b"")
    monkeypatch.setattr(pipeline, "COURT_MODEL", weights)
    return pipeline


def test_court_found_in_every_shot(client, clip, fake_ball, installed, monkeypatch):
    seen = []

    def detector():
        def detect(frame):
            seen.append(frame.shape)
            return np.column_stack([CAM.project(k6y7r_points_3d()), np.full(14, 0.9)])
        return detect
    monkeypatch.setattr(installed, "court_detector", detector)
    v = upload(client, clip)
    assert run_worker_once()["status"] == "done"
    c = stage(client, v["id"], "court")
    assert c["status"] == "done" and c["summary"]["counts"] == {"ok": 2, "needs_review": 0, "failed": 0}
    shots = c["summary"]["shots"]
    assert [(s["start_frame"], s["end_frame"]) for s in shots] == [(0, 24), (25, 49)]
    assert [s["frame"] for s in shots[0]["samples"]][:3] == [0, 5, 10]  # 5 samples per second at 25 fps
    assert len(seen) == sum(len(s["samples"]) for s in shots) and seen[0] == (180, 320, 3)
    assert c["message"] is None


def test_a_shot_without_a_court_fails_and_is_reported(client, clip, fake_ball, installed, monkeypatch):
    def detector():
        kp = np.column_stack([CAM.project(k6y7r_points_3d()), np.full(14, 0.9)])
        # the second shot (frames 25-49, red) shows no court
        return lambda frame: kp if frame[90, 160, 1] > 100 else np.zeros((14, 3))
    monkeypatch.setattr(installed, "court_detector", detector)
    v = upload(client, clip)
    run_worker_once()
    c = stage(client, v["id"], "court")
    assert c["summary"]["counts"] == {"ok": 1, "needs_review": 0, "failed": 1}
    assert c["summary"]["shots"][1]["samples"] == [] and c["summary"]["shots"][1]["error"] is None
    assert "Court found in 1 of 2 camera shots" in c["message"]


def test_without_a_model_the_court_stage_is_unavailable(client, clip, fake_ball, monkeypatch, tmp_path):
    import pipeline
    monkeypatch.setattr(pipeline, "COURT_MODEL", tmp_path / "missing.pt")
    v = upload(client, clip)
    run_worker_once()
    c = stage(client, v["id"], "court")
    assert c["status"] == "unavailable" and "not been trained" in c["message"]
