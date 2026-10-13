import json

from test_actions_api import install
from test_api import run_worker_once, upload


def fake_rally_model(monkeypatch, tmp_path, found):
    from vball import pipeline

    model = tmp_path / "rally.joblib"
    model.write_bytes(b"")
    monkeypatch.setattr(pipeline.config, "RALLY_MODEL", model)
    monkeypatch.setattr("vball.rallies.load_model", lambda path: {"fake": True})
    monkeypatch.setattr(pipeline.models, "rally_cues", lambda video, tick: None)
    monkeypatch.setattr(pipeline.models, "rally_quick_check", lambda video: None)
    monkeypatch.setattr("vball.rallies.detect", lambda model, cues: found)


def test_detected_rallies_replace_demo_and_keep_corrections(client, clip, fake_ball, monkeypatch, tmp_path):
    fake_rally_model(monkeypatch, tmp_path, [(0.1, 0.9, 0.8), (1.1, 1.9, 0.6)])
    v = upload(client, clip)
    assert run_worker_once()["status"] == "done"
    rallies = client.get(f"/videos/{v['id']}/rallies").json()
    assert [(r["start_s"], r["end_s"], r["source"], r["winner"]) for r in rallies] == [
        (0.1, 0.9, "model", None),
        (1.1, 1.9, "model", None),
    ]
    client.patch(f"/videos/{v['id']}/rallies/1", json={"winner": "b"})
    # a rerun finds the second rally slightly shifted: the correction moves to it
    fake_rally_model(monkeypatch, tmp_path, [(0.1, 0.9, 0.8), (1.2, 1.95, 0.6)])
    client.post(f"/videos/{v['id']}/jobs", json={"from_stage": "rallies"})
    assert run_worker_once()["status"] == "done"
    rallies = client.get(f"/videos/{v['id']}/rallies").json()
    assert rallies[1]["start_s"] == 1.2 and rallies[1]["effective_winner"] == "b"


def test_actions_outside_detected_rallies_are_left_out(client, clip, fake_ball, monkeypatch, tmp_path):
    install(monkeypatch, tmp_path, digits=False)  # a spike by track 1 at 0.16-0.4 s
    fake_rally_model(monkeypatch, tmp_path, [(1.5, 1.9, 0.7)])  # the only rally: with its 1 s margin from 0.5 s
    v = upload(client, clip)
    assert run_worker_once()["status"] == "done"
    from vball_app.settings import RESULTS

    assert len(json.loads((RESULTS / v["id"] / "action_events.json").read_text())["events"]) == 1  # stored as found
    a = client.get(f"/videos/{v['id']}/actions").json()
    assert a["events"] == [] and a["suggestions"] == []  # ... but not shown outside play


def test_no_rally_model_keeps_the_stage_unavailable(client, clip, fake_ball):
    v = upload(client, clip)
    run_worker_once()
    s = {x["name"]: x for x in client.get(f"/videos/{v['id']}/stages").json()}["rallies"]
    assert s["status"] == "unavailable" and "rally model is missing" in s["message"]


def test_footage_outside_the_rally_model_is_reported_not_guessed(client, clip, fake_ball, monkeypatch, tmp_path):
    import pandas as pd

    from vball import pipeline

    fake_rally_model(monkeypatch, tmp_path, [(0.1, 0.9, 0.8)])
    gym = pd.DataFrame({"t": [0.0, 0.2, 0.4], "court_ok": [1, 1, 1], "players": [3, 2, 3]})  # few players seen
    monkeypatch.setattr(pipeline.models, "rally_cues", lambda video, tick: gym)
    v = upload(client, clip)
    run_worker_once()
    s = {x["name"]: x for x in client.get(f"/videos/{v['id']}/stages").json()}["rallies"]
    assert s["status"] == "unavailable" and "cannot be told" in s["message"]
    assert all(r["source"] != "model" for r in client.get(f"/videos/{v['id']}/rallies").json())


def test_out_of_training_footage_is_told_from_a_quick_check(client, clip, fake_ball, monkeypatch, tmp_path):
    import pandas as pd

    from vball import pipeline

    fake_rally_model(monkeypatch, tmp_path, [(0.1, 0.9, 0.8)])
    few = pd.DataFrame({"t": [0.0, 1.0], "court_ok": [0, 0], "players": [3, 4]})
    monkeypatch.setattr(pipeline.models, "rally_quick_check", lambda video: few)
    full = []
    monkeypatch.setattr(pipeline.models, "rally_cues", lambda video, tick: full.append(1))
    v = upload(client, clip)
    run_worker_once()
    s = {x["name"]: x for x in client.get(f"/videos/{v['id']}/stages").json()}["rallies"]
    assert s["status"] == "unavailable" and "cannot be told" in s["message"] and full == []  # no full pass


def still_footage(monkeypatch, tmp_path, found):
    """A still camera with an ok court, the fixed-camera model installed (fake), people found on every sampled frame."""
    import numpy as np
    import pandas as pd

    from vball import pipeline

    model = tmp_path / "rally_fixed.joblib"
    model.write_bytes(b"")
    monkeypatch.setattr(pipeline.config, "FIXED_RALLY_MODEL", model)
    monkeypatch.setattr("vball.court_registration.still", lambda *a, **k: True)
    monkeypatch.setattr("vball.court_registration.mapping_at", lambda court, frame, size: np.eye(3))
    calls = {"people": 0}

    def people_boxes(video, n, every):
        calls["people"] += 1
        return pd.DataFrame(
            [(f, 10, 10, 20, 40) for f in range(0, n, every)], columns=["frame", "x1", "y1", "x2", "y2"]
        )

    monkeypatch.setattr(pipeline.models, "people_boxes", people_boxes)
    monkeypatch.setattr("vball.rallies.load_model", lambda path: {"model": path.name})

    def detect(model, cues):
        calls["cues"] = cues
        return found

    monkeypatch.setattr("vball.rallies.detect", detect)
    out = tmp_path / "results"
    out.mkdir()
    pd.DataFrame({"frame": range(50), "visible": 1, "x": 5.0, "y": 5.0}).to_csv(out / "ball.csv", index=False)
    prev = {
        "decode": {"fps": 25.0, "frames": 50, "width": 320, "height": 180},
        "court": {"shots": [{"status": "ok", "samples": [{}], "start_frame": 0, "end_frame": 49}]},
    }
    return out, prev, calls


def test_still_end_line_camera_uses_the_fixed_camera_model(clip, monkeypatch, tmp_path):
    from vball import pipeline

    out, prev, calls = still_footage(monkeypatch, tmp_path, [(0.2, 1.6, 0.7)])
    res = pipeline.rallies.run(clip, out, prev, lambda f: None)
    assert res["status"] == "done" and res["footage"] == "still end-line camera"
    assert res["model"] == "rally_fixed.joblib" and res["rallies"] == [
        {"start_s": 0.2, "end_s": 1.6, "confidence": 0.7}
    ]
    assert "shot" in calls["cues"] and calls["people"] == 1
    pipeline.rallies.run(clip, out, prev, lambda f: None)
    assert calls["people"] == 1  # people boxes are kept in the results folder (people.csv.gz) and reused


def test_still_camera_without_the_fixed_model_is_unavailable(clip, monkeypatch, tmp_path):
    from vball import pipeline

    out, prev, _ = still_footage(monkeypatch, tmp_path, [])
    monkeypatch.setattr(pipeline.config, "FIXED_RALLY_MODEL", tmp_path / "missing.joblib")
    res = pipeline.rallies.run(clip, out, prev, lambda f: None)
    assert res["status"] == "unavailable" and "rally model is missing" in res["message"]


def test_still_camera_with_no_rally_found_says_so(clip, monkeypatch, tmp_path):
    from vball import pipeline

    out, prev, _ = still_footage(monkeypatch, tmp_path, [])
    res = pipeline.rallies.run(clip, out, prev, lambda f: None)
    assert res["status"] == "done" and res["count"] == 0 and "No rally found" in res["message"]
