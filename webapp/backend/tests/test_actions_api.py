import json

from test_api import run_worker_once, upload


def stage(client, vid, name):
    return {s["name"]: s for s in client.get(f"/videos/{vid}/stages").json()}[name]


def install(monkeypatch, tmp_path, digits=True):
    """Fake action and digit models: track 1 (box 130,60-170,100 in the fake players) spikes in frames 6-15,
    and its crop reads 1 then 0 side by side."""
    import pipeline
    for name, path in (("ACTION_MODEL", "action.pt"), ("JERSEY_MODEL", "digits.pt")):
        if name == "JERSEY_MODEL" and not digits:
            continue
        (tmp_path / path).write_bytes(b"")
        monkeypatch.setattr(pipeline, name, tmp_path / path)
    calls = {"frames": 0}

    def action_detector():
        def detect(frame):
            calls["frames"] += 1
            k = calls["frames"] - 1  # sample index; 10 fps of a 25 fps clip -> every 2nd or 3rd frame
            return [("spike", 0.9, 132.0, 58.0, 172.0, 100.0)] if 2 <= k <= 5 else []
        return detect

    def digit_detector():
        return lambda crop: [(1, 0.9, 5.0, 2.0, 15.0, 20.0), (0, 0.8, 18.0, 2.0, 28.0, 20.0)]

    monkeypatch.setattr(pipeline, "action_detector", action_detector)
    monkeypatch.setattr(pipeline, "digit_detector", digit_detector)
    return calls


def test_actions_stage_reports_events_and_numbers(client, clip, fake_ball, monkeypatch, tmp_path):
    install(monkeypatch, tmp_path)
    v = upload(client, clip)
    assert run_worker_once()["status"] == "done"
    a = stage(client, v["id"], "actions")
    assert a["status"] == "done" and a["summary"]["events"] == 1 and a["summary"]["by_action"]["spike"] == 1
    assert a["summary"]["numbered_tracks"] == 1 and a["message"] is None
    from settings import RESULTS
    data = json.loads((RESULTS / v["id"] / "action_events.json").read_text())
    (ev,) = data["events"]
    assert ev["action"] == "spike" and ev["track_id"] == 1 and ev["samples"] == 4
    assert data["numbers"]["1"]["number"] == 10
    assert "2" not in data["numbers"] or data["numbers"]["2"]["readings"] == 0  # the far-away player's crop is tiny


def test_without_the_digit_model_players_keep_tracking_ids(client, clip, fake_ball, monkeypatch, tmp_path):
    install(monkeypatch, tmp_path, digits=False)
    v = upload(client, clip)
    run_worker_once()
    a = stage(client, v["id"], "actions")
    assert a["status"] == "done" and a["summary"]["numbered_tracks"] == 0
    assert "Shirt numbers are not read yet" in a["message"]


def test_without_the_action_model_the_stage_is_unavailable_and_later_stages_run(client, clip, fake_ball):
    v = upload(client, clip)
    assert run_worker_once()["status"] == "done"
    assert stage(client, v["id"], "actions")["status"] == "unavailable"
    assert stage(client, v["id"], "trajectory")["status"] != "pending"
