import numpy as np
import pytest

from test_api import run_worker_once, upload


def test_players_stage_runs_after_ball_without_a_court(client, clip, fake_ball):
    v = upload(client, clip)
    assert run_worker_once()["status"] == "done"
    stages = client.get(f"/videos/{v['id']}/stages").json()
    assert [s["name"] for s in stages] == ["decode", "court", "ball", "players", "trajectory", "events", "rallies"]
    p = {s["name"]: s for s in stages}["players"]
    assert p["status"] == "done" and p["summary"]["tracks"] == 2 and p["summary"]["placed"] is False
    assert "court was not found" in p["message"]

    w = client.get(f"/videos/{v['id']}/players", params={"start": 0.2, "end": 0.24}).json()
    assert w["placed"] is False and w["fps"] == 25
    assert [(b["frame"], b["track_id"]) for b in w["boxes"]] == [(5, 1), (5, 2), (6, 1), (6, 2)]
    assert w["boxes"][0]["court_x"] is None and w["boxes"][0]["side"] is None


def test_with_a_court_mapping_people_off_court_are_dropped(client, clip, fake_ball, monkeypatch):
    import pipeline
    # court -> image: 10 px per metre, origin at (60, 145), court y up the image
    H = [[10.0, 0, 60], [0, -10.0, 145], [0, 0, 1]]
    monkeypatch.setitem(pipeline.FUNCS, "court", lambda *a: {"status": "done", "shots": [
        {"start_frame": 0, "end_frame": 49, "H": H}]})
    v = upload(client, clip)
    assert run_worker_once()["status"] == "done"
    w = client.get(f"/videos/{v['id']}/players", params={"start": 0, "end": 0}).json()
    assert w["placed"] is True
    assert [b["track_id"] for b in w["boxes"]] == [1]  # track 2 maps to y = 12.5 m: 3.5 m beyond the far sideline, outside the 3 m margin
    b = w["boxes"][0]
    assert b["court_x"] == pytest.approx(9.0) and b["court_y"] == pytest.approx(4.5) and b["side"] == "b"


def test_rerun_from_events_reuses_players(client, clip, fake_ball, monkeypatch):
    import pipeline
    v = upload(client, clip)
    run_worker_once()
    calls = []
    monkeypatch.setitem(pipeline.FUNCS, "players", lambda *a: calls.append("players") or {"status": "done"})
    assert client.post(f"/videos/{v['id']}/jobs", json={"from_stage": "events"}).status_code == 201
    assert run_worker_once()["status"] == "done"
    assert calls == []


def test_players_404_before_the_stage_ran(client, clip):
    v = upload(client, clip)
    assert client.get(f"/videos/{v['id']}/players").status_code == 404


def test_homography_lookup_by_shot():
    import pipeline
    at = pipeline.court_homography_at({"shots": [{"start_frame": 0, "end_frame": 9, "H": np.eye(3).tolist()},
                                                 {"start_frame": 10, "end_frame": 19, "H": None}]})
    assert at(5) is not None and at(12) is None and at(30) is None
    assert pipeline.court_homography_at(None)(0) is None
