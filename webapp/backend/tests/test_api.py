import json

import pytest


def upload(client, clip):
    with clip.open("rb") as f:
        r = client.post("/videos", files={"file": ("match.mp4", f, "video/mp4")})
    assert r.status_code == 201, r.text
    return r.json()


def run_worker_once():
    import main
    import worker
    job = main.db.claim_next_job()
    assert job is not None
    worker.process(main.db, job)
    return main.db.get_job(job["id"])


def test_upload_queues_analysis(client, clip):
    v = upload(client, clip)
    assert (v["fps"], v["width"], v["height"]) == (25, 320, 180)
    assert v["job"]["status"] == "queued"
    assert client.post(f"/videos/{v['id']}/jobs", json={}).status_code == 409
    assert any(x["id"] == v["id"] for x in client.get("/videos").json())


def test_rejects_non_video(client):
    r = client.post("/videos", files={"file": ("notes.txt", b"hello", "text/plain")})
    assert r.status_code == 400


def test_pipeline_stages_and_ball_window(client, clip, fake_ball, monkeypatch, tmp_path):
    import pipeline
    monkeypatch.setattr(pipeline, "COURT_MODEL", tmp_path / "missing.pt")  # independent of models/
    v = upload(client, clip)
    job = run_worker_once()
    assert job["status"] == "done", job["error"]
    assert job["progress"] == 1.0

    stages = {s["name"]: s for s in client.get(f"/videos/{v['id']}/stages").json()}
    assert stages["decode"]["status"] == "done"
    assert [s["start_frame"] for s in stages["decode"]["summary"]["shots"]] == [0, 25]
    assert stages["court"]["status"] == "unavailable"
    assert stages["ball"]["summary"]["detected"] == 25
    assert stages["rallies"]["status"] == "todo"

    w = client.get(f"/videos/{v['id']}/ball", params={"start": 0.2, "end": 0.4}).json()
    assert w["frame"] == [5, 6, 7, 8, 9, 10]
    assert w["x"][0] is None and w["x"][1] == 16.0


def test_rerun_reuses_earlier_stages(client, clip, fake_ball, monkeypatch):
    import pipeline
    v = upload(client, clip)
    run_worker_once()
    calls = []
    monkeypatch.setitem(pipeline.FUNCS, "decode", lambda *a: calls.append("decode") or {"status": "done"})
    assert client.post(f"/videos/{v['id']}/jobs", json={"from_stage": "ball"}).status_code == 201
    assert run_worker_once()["status"] == "done"
    assert calls == []  # decode result reused


def test_job_stream_ends_with_final_state(client, clip, fake_ball):
    v = upload(client, clip)
    run_worker_once()
    with client.stream("GET", f"/videos/{v['id']}/jobs/stream") as r:
        events = [json.loads(line[6:]) for line in r.iter_lines() if line.startswith("data: ")]
    assert events[-1]["status"] == "done"


def test_video_file_supports_seeking(client, clip):
    v = upload(client, clip)
    r = client.get(f"/videos/{v['id']}/file", headers={"Range": "bytes=0-99"})
    assert r.status_code == 206 and len(r.content) == 100


@pytest.fixture
def rallies(client, clip):
    import main
    v = upload(client, clip)
    main.db.replace_rallies(v["id"], [
        {"idx": i, "start_s": i, "end_s": i + 0.5, "winner": w, "source": "demo"}
        for i, w in enumerate(["a", "b", None])
    ])
    return v["id"]


def test_rally_scores_and_correction(client, rallies):
    r = client.get(f"/videos/{rallies}/rallies").json()
    assert [(x["score"]["a"], x["score"]["b"]) for x in r] == [(1, 0), (1, 1), (1, 1)]

    r = client.patch(f"/videos/{rallies}/rallies/2", json={"winner": "a"}).json()
    assert r[2]["winner"] is None and r[2]["effective_winner"] == "a"
    assert (r[2]["score"]["a"], r[2]["score"]["b"]) == (2, 1)

    r = client.patch(f"/videos/{rallies}/rallies/2", json={"winner": None}).json()
    assert r[2]["effective_winner"] is None
    assert client.patch(f"/videos/{rallies}/rallies/9", json={"winner": "a"}).status_code == 404


def test_delete_removes_upload(client, clip):
    import main
    from pathlib import Path
    v = upload(client, clip)
    path = Path(main.db.get_video(v["id"])["path"])
    assert client.delete(f"/videos/{v['id']}").status_code == 204
    assert not path.exists()
    assert client.get(f"/videos/{v['id']}").status_code == 404


def test_score_summary_absent_without_rallies(client, clip):
    v = upload(client, clip)
    assert v["score"] is None


def test_score_summary_after_last_rally(client, clip):
    import main
    v = upload(client, clip)
    winners = ["a"] * 25 + ["b"] * 10 + ["a"] * 12  # set 1 to A 25-0, set 2 at 12-10
    main.db.replace_rallies(v["id"], [
        {"idx": i, "start_s": i, "end_s": i + 0.5, "winner": w, "source": "model"} for i, w in enumerate(winners)
    ])
    client.patch(f"/videos/{v['id']}/rallies/0", json={"winner": "a"})
    s = next(x for x in client.get("/videos").json() if x["id"] == v["id"])["score"]
    assert (s["sets_a"], s["sets_b"], s["set_no"], s["a"], s["b"]) == (1, 0, 2, 12, 10)
    assert (s["rallies"], s["corrected"], s["demo"]) == (47, 1, False)


def test_score_summary_flags_demo(client, rallies):
    s = client.get(f"/videos/{rallies}").json()["score"]
    assert s["demo"] is True and s["rallies"] == 3


def test_stage_is_visible_while_it_runs(client, clip, monkeypatch):
    """A client polling the job during ball tracking must see the ball stage, not the previous one."""
    import main
    import pipeline
    v = upload(client, clip)
    seen = {}

    def ball_stage(video, out, prev, tick):
        seen["stage"] = main.db.latest_job(v["id"])["stage"]
        return {"status": "done", "frames": 0, "detected": 0}

    monkeypatch.setitem(pipeline.FUNCS, "ball", ball_stage)
    run_worker_once()
    assert seen["stage"] == "ball"


def test_ball_coverage(client, clip, fake_ball):
    v = upload(client, clip)
    assert client.get(f"/videos/{v['id']}/ball/coverage").status_code == 404  # not tracked yet
    run_worker_once()
    r = client.get(f"/videos/{v['id']}/ball/coverage", params={"bins": 5}).json()
    assert r["duration_s"] == 2.0
    assert r["coverage"] == [0.5] * 5  # fake ball: seen on even frames only
    assert client.get(f"/videos/{v['id']}/ball/coverage", params={"bins": 0}).status_code == 422
    assert client.get(f"/videos/{v['id']}/ball/coverage", params={"bins": 5000}).status_code == 422


def test_ball_coverage_first_half_only(client, clip, monkeypatch):
    import pandas as pd
    import numpy as np
    import pipeline
    n = 50
    f = np.arange(n)
    monkeypatch.setattr(pipeline.ball, "track", lambda *a, **k: pd.DataFrame(
        {"frame": f, "visible": (f < n // 2).astype(int), "x": 1.0, "y": 1.0, "radius": 5}))
    v = upload(client, clip)
    run_worker_once()
    cov = client.get(f"/videos/{v['id']}/ball/coverage", params={"bins": 10}).json()["coverage"]
    assert cov == [1.0] * 5 + [0.0] * 5
