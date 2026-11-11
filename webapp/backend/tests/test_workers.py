"""Several workers on one database: leases, reclaiming, clean stop, stage timings (change scale-out-analysis-workers).

These tests use their own database file under tmp_path, never the app's."""

import multiprocessing as mp
import os
import signal
import threading
import time
from pathlib import Path

import pytest
from vball_app.db import Database


def jobs_db(path, n: int) -> Database:
    db = Database(path)
    vid = db.add_video("v", "/nowhere.mp4", {})["id"]
    for _ in range(n):  # one video is enough: the API, not the database, allows one active job per video
        db.add_job(vid, "decode")
    return db


def steal(db: Database, jid: str, worker_id: str) -> None:
    """Another worker took the job (as after an expired lease)."""
    with db.connect() as c:
        c.execute("UPDATE jobs SET worker_id = ? WHERE id = ?", (worker_id, jid))


def _claim_all(path, worker_id, out):
    db = Database(path)
    got = []
    while (job := db.claim_next_job(worker_id)) is not None:
        got.append(job["id"])
        db.update_job(job["id"], worker_id, status="done")
    out.put(got)


def test_concurrent_claims_take_each_job_once(tmp_path):
    path = tmp_path / "jobs.db"
    db = jobs_db(path, 100)
    ctx = mp.get_context("spawn")
    out = ctx.Queue()
    procs = [ctx.Process(target=_claim_all, args=(path, f"w{i}", out)) for i in range(4)]
    for p in procs:
        p.start()
    claimed = [j for _ in procs for j in out.get(timeout=120)]
    for p in procs:
        p.join()
    assert len(claimed) == 100 and len(set(claimed)) == 100
    with db.connect() as c:
        assert c.execute("SELECT COUNT(*) FROM jobs WHERE status = 'done' AND attempts = 1").fetchone()[0] == 100


def test_second_worker_leaves_a_held_job_alone(tmp_path):
    db = jobs_db(tmp_path / "jobs.db", 1)
    job = db.claim_next_job("a")
    assert db.claim_next_job("b") is None  # a fresh Database at worker start changes nothing either
    Database(tmp_path / "jobs.db")
    j = db.get_job(job["id"])
    assert (j["status"], j["worker_id"]) == ("running", "a")


def test_expired_lease_is_taken_by_another_worker(tmp_path):
    db = jobs_db(tmp_path / "jobs.db", 1)
    job = db.claim_next_job("a", lease_s=0.05)
    time.sleep(0.1)
    again = db.claim_next_job("b")
    assert again["id"] == job["id"] and again["worker_id"] == "b" and again["attempts"] == 2
    # the dead worker's late writes are refused, the new holder's are not
    assert not db.update_job(job["id"], "a", status="failed", error="late")
    assert not db.renew_lease(job["id"], "a")
    assert db.update_job(job["id"], "b", status="done")
    assert db.get_job(job["id"])["status"] == "done"


def test_job_that_keeps_losing_workers_fails(tmp_path):
    db = jobs_db(tmp_path / "jobs.db", 1)
    for w in ("a", "b"):
        db.claim_next_job(w, lease_s=0.01, max_attempts=2)
        time.sleep(0.03)
    assert db.claim_next_job("c", max_attempts=2) is None
    j = db.get_job(db.latest_job(db.list_videos()[0]["id"])["id"])
    assert j["status"] == "failed" and j["error"] == "worker lost 2 times" and j["worker_id"] is None


def test_release_queues_the_job_without_counting_an_attempt(tmp_path):
    db = jobs_db(tmp_path / "jobs.db", 1)
    job = db.claim_next_job("a")
    assert not db.release_job(job["id"], "b")  # only the holder can release
    assert db.release_job(job["id"], "a")
    j = db.get_job(job["id"])
    assert (j["status"], j["worker_id"], j["attempts"]) == ("queued", None, 0)


def test_heartbeat_keeps_the_lease_and_notices_a_lost_one(tmp_path):
    from vball_app.worker import Heartbeat

    db = jobs_db(tmp_path / "jobs.db", 1)
    job = db.claim_next_job("a", lease_s=0.15)
    with Heartbeat(db, job["id"], "a", lease_s=0.15) as hb:
        time.sleep(0.4)  # longer than the lease: only renewal keeps it
        assert db.claim_next_job("b") is None and not hb.lost.is_set()
        steal(db, job["id"], "b")
        assert hb.lost.wait(1.0)


def test_process_records_stage_timings_and_skips_reused(tmp_path, monkeypatch):
    from vball_app import worker

    from vball import pipeline

    db = jobs_db(tmp_path / "jobs.db", 1)
    job = db.claim_next_job("a")

    def run(video, out, from_stage, on_progress, court_corrections=None, on_stage_done=None):
        for s, sec, reused in (("decode", 0, True), ("ball", 1.5, False), ("rallies", 0.25, False)):
            on_progress(s, 0.5)
            on_stage_done(s, sec, reused)
        return {}

    monkeypatch.setattr(pipeline, "run", run)
    monkeypatch.setattr(worker.backup, "back_up_if_due", lambda: None)
    worker.process(db, job, "a")
    j = db.get_job(job["id"])
    assert j["status"] == "done" and j["timings"] == {"ball": 1.5, "rallies": 0.25} and j["worker_id"] is None


def test_lost_lease_drops_the_run_without_writing(tmp_path, monkeypatch):
    from vball_app import worker

    from vball import pipeline

    db = jobs_db(tmp_path / "jobs.db", 1)
    job = db.claim_next_job("a")

    def run(video, out, from_stage, on_progress, court_corrections=None, on_stage_done=None):
        steal(db, job["id"], "b")  # taken over while this run stalled
        time.sleep(0.2)
        on_progress("ball", 0.5)
        raise AssertionError("not reached: the lost lease stops the run")

    monkeypatch.setattr(pipeline, "run", run)
    worker.process(db, job, "a", lease_s=0.15)
    j = db.get_job(job["id"])
    assert (j["status"], j["worker_id"], j["error"]) == ("running", "b", None)


def _worker_loop(data, ready):
    os.environ["VBALL_WEBAPP_DATA"] = str(data)
    from vball_app import worker

    from vball import pipeline

    def run(video, out, from_stage, on_progress, **kw):
        ready.set()
        while True:  # a long stage
            time.sleep(0.05)
            on_progress("ball", 0.1)

    pipeline.run = run
    worker.run_worker(poll_s=0.05)


@pytest.mark.parametrize("sig", [signal.SIGTERM, signal.SIGINT])
def test_stop_signal_queues_the_job_again(tmp_path, sig):
    data = tmp_path / "data"
    db = jobs_db(data / "webapp.db", 1)
    ctx = mp.get_context("spawn")
    ready = ctx.Event()
    p = ctx.Process(target=_worker_loop, args=(data, ready))
    p.start()
    assert ready.wait(60), "worker never started the job"
    os.kill(p.pid, sig)
    p.join(30)
    j = db.get_job(db.latest_job(db.list_videos()[0]["id"])["id"])
    assert (j["status"], j["worker_id"], j["attempts"]) == ("queued", None, 0)


def test_threads_do_not_double_claim(tmp_path):
    jobs_db(tmp_path / "jobs.db", 30)
    got: list[str] = []
    lock = threading.Lock()

    def take(w):
        mine = Database(tmp_path / "jobs.db")
        while (j := mine.claim_next_job(w)) is not None:
            with lock:
                got.append(j["id"])

    ts = [threading.Thread(target=take, args=(f"t{i}",)) for i in range(6)]
    for t in ts:
        t.start()
    for t in ts:
        t.join()
    assert len(got) == 30 == len(set(got))


def test_run_worker_releases_its_job_on_stop(monkeypatch):
    """In-process version of the signal test: a Stop raised during a job (as the signal handler does) queues it."""
    from vball_app import deps, worker

    vid = deps.db.add_video("v", "/nowhere.mp4", {})["id"]
    jid = deps.db.add_job(vid, "decode")["id"]
    monkeypatch.setattr(worker, "configure_logging", lambda: None)
    monkeypatch.setattr(worker.signal, "signal", lambda *a: None)
    monkeypatch.setattr(worker, "process", lambda db, job, wid, lease: worker._raise_stop(signal.SIGTERM, None))
    monkeypatch.setattr(worker, "limit_threads", lambda n: None)
    worker.run_worker(threads=2)
    j = deps.db.get_job(jid)
    assert (j["status"], j["worker_id"]) == ("queued", None)


def test_run_worker_idles_until_stopped(monkeypatch):
    from vball_app import worker

    monkeypatch.setattr(worker, "configure_logging", lambda: None)
    monkeypatch.setattr(worker.signal, "signal", lambda *a: None)
    monkeypatch.setattr(worker.time, "sleep", lambda s: worker._raise_stop(signal.SIGINT, None))
    worker.run_worker()  # no job queued: polls once, then stops cleanly


def test_main_starts_one_or_several_workers(monkeypatch):
    from vball_app import worker

    started = []
    monkeypatch.setattr(worker, "configure_logging", lambda: None)
    monkeypatch.setattr(worker, "check_models", lambda: {})
    monkeypatch.setattr(worker.backup, "back_up", lambda: None)
    monkeypatch.setattr(worker, "run_worker", lambda threads, lease: started.append(("inline", threads, lease)))

    class Proc:
        def __init__(self, target, args, name):
            self.args = args

        def start(self):
            started.append(("process", *self.args))

        def join(self):
            pass

        def terminate(self):
            pass

    monkeypatch.setattr(worker.mp, "get_context", lambda kind: type("Ctx", (), {"Process": Proc}))
    monkeypatch.setattr(worker.signal, "signal", lambda *a: None)
    monkeypatch.setattr(worker.os, "cpu_count", lambda: 8)
    monkeypatch.setattr("sys.argv", ["worker"])
    worker.main()
    monkeypatch.setattr("sys.argv", ["worker", "--workers", "4", "--lease", "30"])
    worker.main()
    assert started == [("inline", None, 60.0)] + [("process", 2, 30.0)] * 4


def test_limit_threads_sets_every_library(monkeypatch):
    import torch
    from vball_app import worker

    for var in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "VBALL_THREADS"):
        monkeypatch.delenv(var, raising=False)
    calls = []
    monkeypatch.setattr("cv2.setNumThreads", calls.append)
    monkeypatch.setattr(torch, "set_num_threads", calls.append)
    worker.limit_threads(3)
    assert os.environ["VBALL_THREADS"] == os.environ["OMP_NUM_THREADS"] == "3" and calls == [3, 3]


def test_benchmark_runs_jobs_and_sums_stage_times(tmp_path, monkeypatch, clip):
    """vball_app.bench with the worker command replaced: a fake process that finishes every job at once."""
    from vball_app import bench

    class FakeWorker:
        pid = os.getpid()

        def __init__(self, cmd, env, stdout, stderr):
            db = Database(Path(env["VBALL_WEBAPP_DATA"]) / "webapp.db")
            assert cmd[-4:] == ["--workers", "2", "--lease", "20.0"]
            while (j := db.claim_next_job("fake")) is not None:
                db.update_job(j["id"], "fake", status="done", timings={"ball": 1.0, "court": 2.0})

        def send_signal(self, sig):
            pass

        def wait(self, timeout):
            pass

    monkeypatch.setattr(bench.subprocess, "Popen", FakeWorker)
    r = bench.run([clip], workers=2, copies=3, keep=tmp_path)
    assert (r["jobs"], r["done"], r["failed"], r["attempts"]) == (3, 3, [], [1, 1, 1])
    assert r["stage_s"] == {"court": 6.0, "ball": 3.0} and r["peak_rss_gb"] > 0
    assert '"workers": 2' in bench.to_json([r])
