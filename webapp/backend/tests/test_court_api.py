import numpy as np
import pytest
from test_api import run_worker_once, upload

from vball.calibration import look_at
from vball.court_keypoints import k6y7r_points_3d

CAM = look_at([9.0, -14.0, 7.5], [9.0, 4.5, 0.5], 300.0, (320, 180))  # the 320 x 180 test clip


def stage(client, vid, name):
    return {s["name"]: s for s in client.get(f"/videos/{vid}/stages").json()}[name]


@pytest.fixture
def installed(monkeypatch, tmp_path):
    from vball import pipeline

    weights = tmp_path / "court_kpt.pt"
    weights.write_bytes(b"")
    monkeypatch.setattr(pipeline.config, "COURT_MODELS", {"gym": weights})
    return pipeline.models


def test_court_found_in_every_shot(client, clip, fake_ball, installed, monkeypatch):
    seen = []

    def detector(weights):
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
    def detector(weights):
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
    from vball import pipeline

    monkeypatch.setattr(pipeline.config, "COURT_MODELS", {"gym": tmp_path / "missing.pt"})
    v = upload(client, clip)
    run_worker_once()
    c = stage(client, v["id"], "court")
    assert c["status"] == "unavailable" and "court model is missing" in c["message"]


def test_each_shot_uses_the_model_that_found_its_court(client, clip, fake_ball, monkeypatch, tmp_path):
    from vball import pipeline

    for name in ("gym", "broadcast"):
        (tmp_path / f"{name}.pt").write_bytes(b"")
    monkeypatch.setattr(pipeline.config, "COURT_MODELS", {n: tmp_path / f"{n}.pt" for n in ("gym", "broadcast")})
    kp = np.column_stack([CAM.project(k6y7r_points_3d()), np.full(14, 0.9)])

    def detector(weights):
        first_shot = weights.stem == "gym"  # the gym model finds the court in shot 1 (green), broadcast in shot 2 (red)
        return lambda frame: kp if (frame[90, 160, 1] > 100) == first_shot else np.zeros((14, 3))

    monkeypatch.setattr(pipeline.models, "court_detector", detector)
    v = upload(client, clip)
    run_worker_once()
    c = stage(client, v["id"], "court")
    assert c["summary"]["counts"] == {"ok": 2, "needs_review": 0, "failed": 0}
    assert [s["model"] for s in c["summary"]["shots"]] == ["gym", "broadcast"]
    assert c["summary"]["models"] == {"gym": "gym.pt", "broadcast": "broadcast.pt"}


def failing_court(installed, monkeypatch):
    """A court model that finds nothing: every shot fails, so only a correction gives a court."""
    monkeypatch.setattr(installed, "court_detector", lambda weights: lambda frame: np.zeros((14, 3)))


CORNERS = CAM.project(k6y7r_points_3d()[[0, 4, 5, 9]]).tolist()  # the true corners of the test camera


def test_court_correction_places_players_and_survives_a_rerun(client, clip, fake_ball, installed, monkeypatch):
    failing_court(installed, monkeypatch)
    v = upload(client, clip)
    assert run_worker_once()["status"] == "done"
    court = client.get(f"/videos/{v['id']}/court").json()
    assert court["status"] == "done" and [s["status"] for s in court["shots"]] == ["failed", "failed"]
    assert client.get(f"/videos/{v['id']}/players?start=0&end=0.9").json()["placed"] is False

    r = client.put(f"/videos/{v['id']}/court/0", json={"frame": 10, "points_px": CORNERS})
    assert r.status_code == 200 and r.json()["queued"] is True
    shot = r.json()["court"]["shots"][0]
    assert shot["status"] == "ok" and shot["corrected"] and np.allclose(shot["samples"][0]["corners_px"], CORNERS)
    job = run_worker_once()
    assert job["status"] == "done" and job["from_stage"] == "players"
    assert stage(client, v["id"], "court")["message"].endswith("1 camera shot set by you.")
    players = client.get(f"/videos/{v['id']}/players?start=0&end=0.9").json()
    assert players["placed"] is True and any(b["court_x"] is not None for b in players["boxes"])

    client.post(f"/videos/{v['id']}/jobs", json={"from_stage": "decode"})
    assert run_worker_once()["status"] == "done"
    assert client.get(f"/videos/{v['id']}/court").json()["shots"][0]["corrected"] is True

    r = client.delete(f"/videos/{v['id']}/court/0")
    assert r.status_code == 200 and r.json()["court"]["shots"][0]["status"] == "failed"


def test_court_correction_errors(client, clip, fake_ball, installed, monkeypatch):
    failing_court(installed, monkeypatch)
    v = upload(client, clip)
    run_worker_once()
    vid = v["id"]
    assert client.put(f"/videos/{vid}/court/7", json={"frame": 10, "points_px": CORNERS}).status_code == 404
    assert client.put(f"/videos/{vid}/court/0", json={"frame": 40, "points_px": CORNERS}).status_code == 422
    crossed = [CORNERS[0], CORNERS[3], CORNERS[2], CORNERS[1]]
    assert client.put(f"/videos/{vid}/court/0", json={"frame": 10, "points_px": crossed}).status_code == 422
    assert (
        client.put(f"/videos/{vid}/court/0", json={"frame": 10, "points_px": CORNERS, "preset": "nope"}).status_code
        == 422
    )
    assert client.delete(f"/videos/{vid}/court/0").status_code == 404
    assert client.get("/videos/nope/court").status_code == 404


def test_near_half_correction(client, clip, fake_ball, installed, monkeypatch):
    failing_court(installed, monkeypatch)
    v = upload(client, clip)
    run_worker_once()
    near = CAM.project(k6y7r_points_3d()[[2, 7, 9, 0]]).tolist()  # centre line left / right, end line right / left
    r = client.put(f"/videos/{v['id']}/court/1", json={"frame": 30, "points_px": near, "preset": "near_half"})
    assert r.status_code == 200, r.text
    assert np.allclose(r.json()["court"]["shots"][1]["samples"][0]["corners_px"], CORNERS, atol=1e-6)


def test_no_second_job_while_one_is_active(client, clip, fake_ball, installed, monkeypatch):
    from vball_app import deps

    failing_court(installed, monkeypatch)
    v = upload(client, clip)
    run_worker_once()
    client.post(f"/videos/{v['id']}/jobs", json={"from_stage": "ball"})  # queued, not yet run
    r = client.put(f"/videos/{v['id']}/court/0", json={"frame": 10, "points_px": CORNERS})
    assert r.json()["queued"] is False
    with deps.db.connect() as c:
        assert (
            c.execute("SELECT COUNT(*) FROM jobs WHERE video_id = ? AND status = 'queued'", (v["id"],)).fetchone()[0]
            == 1
        )
    run_worker_once()  # the queued job reads the correction when it reaches the court stage
    players = client.get(f"/videos/{v['id']}/players?start=0&end=0.9").json()
    assert players["placed"] is True
