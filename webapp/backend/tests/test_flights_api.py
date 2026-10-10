import numpy as np
import pandas as pd
import pytest
from vball.calibration import look_at
from vball.court_keypoints import k6y7r_points_3d
from vball.trajectory.synthetic import render

from test_api import run_worker_once, upload

SIZE = (320, 180)  # the test clip
CAM = look_at([9.0, -14.0, 7.5], [9.0, 4.5, 0.5], 300.0, SIZE)
# one flight across the view over the clip's 50 frames at 25 fps
ARC = render(CAM, [[2.0, 3.0, 2.5], [15.0, 6.0, 2.0]], [1.96], fps=25.0)  # ends in the air


def court_keypoints(camera=CAM):
    """14 x (x, y, conf) as the court model would return for this camera."""
    return np.column_stack([camera.project(k6y7r_points_3d()), np.full(14, 0.9)])


@pytest.fixture
def calibrated(monkeypatch, tmp_path):
    """The real court stage with a fake detector seeing the synthetic camera; ball stage with the arc."""
    import pipeline
    weights = tmp_path / "court_kpt.pt"
    weights.write_bytes(b"")
    monkeypatch.setattr(pipeline, "COURT_MODELS", {"gym": weights})
    monkeypatch.setattr(pipeline, "court_detector", lambda weights: (lambda frame: court_keypoints()))

    def track(video, model, out_dir=None, force=False):
        uv = ARC.uv
        return pd.DataFrame({"frame": np.arange(len(uv)), "visible": 1, "x": uv[:, 0], "y": uv[:, 1], "radius": 3})
    monkeypatch.setattr(pipeline.ball, "track", track)


def stage(client, vid, name):
    return {s["name"]: s for s in client.get(f"/videos/{vid}/stages").json()}[name]


def test_without_a_court_there_are_no_flights_and_the_reason_is_given(client, clip, fake_ball):
    v = upload(client, clip)
    assert run_worker_once()["status"] == "done"
    t = stage(client, v["id"], "trajectory")
    assert t["status"] == "done" and t["summary"]["flights"] == 0 and "could not be calibrated" in t["message"]
    assert client.get(f"/videos/{v['id']}/flights").json() == []


def test_court_stage_to_3d_flights_end_to_end(client, clip, calibrated):
    v = upload(client, clip)
    assert run_worker_once()["status"] == "done"
    court = stage(client, v["id"], "court")
    assert court["status"] == "done" and court["summary"]["counts"] == {"ok": 2, "needs_review": 0, "failed": 0}
    # the clip has a camera cut at frame 25, so the arc is fitted once per shot
    t = stage(client, v["id"], "trajectory")
    assert t["summary"]["calibrated_shots"] == 2 and t["summary"]["flights"] == 2
    flights = client.get(f"/videos/{v['id']}/flights").json()
    for f in flights:
        # each half lasts ~1 s on a 320 x 180 camera, so the depth sd (1 px noise floor) flags it low
        # quality; the actual error is still a few centimetres
        assert f["source"] == "model" and f["landing"] is None
        pos = np.array([[s["x"], s["y"], s["z"]] for s in f["samples"]])
        first = round(f["start_s"] * 25)
        err = np.linalg.norm(pos - ARC.positions[first:first + len(pos)], axis=1)
        assert np.median(err) < 0.05  # noise-free detections
        assert all(s["observed"] for s in f["samples"])
    assert any(f["net_crossing"] and f["net_crossing"]["height_m"] > 1.0 for f in flights)


def test_an_unusable_calibration_is_reported(client, clip, fake_ball, monkeypatch):
    import pipeline
    # a shot the court stage accepted, but whose keypoints fit no camera
    kp = np.column_stack([np.random.default_rng(0).uniform(0, 300, (14, 2)), np.full(14, 0.9)]).tolist()
    corners = [[40, 60], [280, 60], [310, 170], [10, 170]]
    monkeypatch.setitem(pipeline.FUNCS, "court", lambda *a: {"status": "done", "shots": [
        {"start_frame": 0, "end_frame": 49, "status": "ok", "error": 0.001,
         "samples": [{"frame": 0, "corners_px": corners, "error": 0.001, "keypoints": kp}]}]})
    v = upload(client, clip)
    run_worker_once()
    t = stage(client, v["id"], "trajectory")
    assert t["summary"]["flights"] == 0 and t["summary"]["calibrated_shots"] == 0
    assert "could not be calibrated" in t["message"]


def test_demo_rallies_get_demo_flights_landing_at_the_rally_landing(client, clip):
    import main
    v = upload(client, clip)
    main.db.replace_rallies(v["id"], [{"idx": 0, "start_s": 0.0, "end_s": 6.0, "winner": "a", "reason": "in",
                                       "landing_x": 14.0, "landing_y": 3.0, "source": "demo"}])
    fl = client.get(f"/videos/{v['id']}/flights").json()
    assert len(fl) == 4 and {f["source"] for f in fl} == {"demo"}
    assert fl[-1]["landing"] == pytest.approx({"x_m": 14.0, "y_m": 3.0}, abs=0.05)
    assert fl[0]["net_crossing"]["height_m"] > 2.43  # the serve clears the net
    assert fl[-1]["samples"][0]["x"] < 9  # the attack comes from the other half
    window = client.get(f"/videos/{v['id']}/flights", params={"start": 3.5, "end": 3.6}).json()
    assert len(window) == 1 and window[0]["start_s"] == pytest.approx(3.1, abs=0.05)  # the attack


def test_a_short_demo_rally_keeps_only_the_last_flights(client, clip):
    import main
    v = upload(client, clip)
    main.db.replace_rallies(v["id"], [{"idx": 0, "start_s": 0.0, "end_s": 1.2, "winner": "b", "reason": "in",
                                       "landing_x": 4.0, "landing_y": 4.0, "source": "demo"}])
    fl = client.get(f"/videos/{v['id']}/flights").json()
    assert len(fl) == 1 and fl[0]["end_s"] - fl[0]["start_s"] == pytest.approx(0.5, abs=0.05)


def test_flights_404_before_the_stage_ran(client, clip):
    v = upload(client, clip)
    assert client.get(f"/videos/{v['id']}/flights").status_code == 404


def test_every_demo_flight_that_crosses_the_net_clears_it():
    import random

    import demo
    rallies = demo.demo_rallies(600.0, random.Random(1))  # 300 rallies with random landings
    flights = demo.demo_flights([{**r, "end_s": r["start_s"] + 5.0} for r in rallies], 25.0)
    crossings = [f["derived"]["net_crossing"]["height_m"] for f in flights if f["derived"]["net_crossing"]]
    assert len(crossings) > 300 and min(crossings) > 2.43


def test_samples_without_keypoints_do_not_break_the_stage(client, clip, fake_ball, monkeypatch):
    import pipeline
    corners = [[40, 60], [280, 60], [310, 170], [10, 170]]
    monkeypatch.setitem(pipeline.FUNCS, "court", lambda *a: {"status": "done", "shots": [
        {"start_frame": 0, "end_frame": 49, "status": "ok", "error": 0.001,
         "samples": [{"frame": 0, "corners_px": corners, "error": 0.001, "keypoints": []}]}]})
    v = upload(client, clip)
    assert run_worker_once()["status"] == "done"
    t = stage(client, v["id"], "trajectory")
    assert t["summary"]["flights"] == 0 and "no court keypoints" in t["message"]
