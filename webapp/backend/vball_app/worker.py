"""Analysis workers: take queued jobs from SQLite and run the pipeline.

Usage: python -m vball_app.worker [--workers N]   (next to the API: uvicorn vball_app.main:app)

Several workers may share one database (change scale-out-analysis-workers). A worker holds a lease on its job and
renews it from a heartbeat thread; a job whose lease runs out (its worker died) is taken by another worker. Ctrl-C or
SIGTERM puts the current job back in the queue at once.
"""

import argparse
import logging
import multiprocessing as mp
import os
import signal
import socket
import threading
import time
import uuid
from pathlib import Path
from typing import Any

from vball import pipeline

from . import backup
from .db import LEASE_S, Database
from .settings import DB_PATH, RESULTS, configure_logging
from .startup import check_models

POLL_S = 1.0
log = logging.getLogger(__name__)


class LeaseLost(Exception):
    """Another worker took the job after this worker's lease ran out (it stalled); stop without writing."""


class Stop(BaseException):
    """SIGTERM or SIGINT: release the job and exit. A BaseException so stage code catching Exception lets it pass."""


def new_worker_id() -> str:
    return f"{socket.gethostname().split('.')[0]}-{os.getpid()}-{uuid.uuid4().hex[:4]}"


class Heartbeat:
    """Renews a job's lease every LEASE_S / 3 on a thread; `lost` is set when the job is no longer ours."""

    def __init__(self, db: Database, jid: str, worker_id: str, lease_s: float = LEASE_S):
        self.lost = threading.Event()
        self._stop = threading.Event()
        self._args = (db, jid, worker_id, lease_s)
        self._thread = threading.Thread(target=self._run, daemon=True)

    def _run(self):
        db, jid, worker_id, lease_s = self._args
        while not self._stop.wait(lease_s / 3):
            if not db.renew_lease(jid, worker_id, lease_s):
                self.lost.set()
                return

    def __enter__(self):
        self._thread.start()
        return self

    def __exit__(self, *exc):
        self._stop.set()
        self._thread.join()


def process(db: Database, job: dict, worker_id: str | None = None, lease_s: float = LEASE_S) -> None:
    """Run one claimed job. With `worker_id` the lease is renewed while it runs and every write is guarded by it."""
    jid = job["id"]
    video = db.get_video(job["video_id"])
    if video is None:  # deleted while queued
        db.update_job(jid, worker_id, status="failed", error="video deleted")
        return
    last: dict[str, Any] = {"stage": None, "p": 0.0}
    timings: dict[str, float] = {}

    with Heartbeat(db, jid, worker_id, lease_s) if worker_id else _NoHeartbeat() as hb:

        def on_progress(stage: str, p: float):
            if hb.lost.is_set():
                raise LeaseLost(jid)
            # Throttle progress writes, but always record a stage change: a stage can start at the
            # same overall progress the previous one ended with.
            if stage != last["stage"] or p - last["p"] >= 0.01 or p >= 1:
                db.update_job(jid, worker_id, stage=stage, progress=round(p, 3))
                last.update(stage=stage, p=p)

        def on_stage_done(stage: str, seconds: float, reused: bool):
            if not reused:
                timings[stage] = seconds

        try:
            out = pipeline.run(
                Path(video["path"]),
                RESULTS / video["id"],
                job["from_stage"],
                on_progress,
                court_corrections=lambda: db.court_corrections(video["id"]),
                on_stage_done=on_stage_done,
            )
            if hb.lost.is_set():
                raise LeaseLost(jid)
            r = out.get("rallies") or {}
            if r.get("status") == "done":  # detected rallies replace demo or earlier ones; corrections move along
                db.replace_detected_rallies(video["id"], r.get("rallies", []))
            db.update_job(jid, worker_id, status="done", stage=None, progress=1.0, timings=timings)
            backup.back_up_if_due()
        except LeaseLost:
            log.warning("job %s: lease lost, another worker has it; dropping this run", jid)
        except Exception as e:
            log.exception("job %s failed", jid)
            db.update_job(jid, worker_id, status="failed", error=f"{type(e).__name__}: {e}"[:500], timings=timings)


class _NoHeartbeat:
    lost = threading.Event()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        pass


def limit_threads(n: int) -> None:
    """Cap the compute threads of this process (set before models load): OpenMP / BLAS through the environment,
    ONNX Runtime through VBALL_THREADS (vball.ball_detect), OpenCV and PyTorch directly."""
    for var in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "VBALL_THREADS"):
        os.environ[var] = str(n)
    import cv2

    cv2.setNumThreads(n)
    try:
        import torch

        torch.set_num_threads(n)
    except ImportError:
        pass


def _raise_stop(signum, frame):
    raise Stop(signal.Signals(signum).name)


def run_worker(threads: int | None = None, lease_s: float = LEASE_S, poll_s: float = POLL_S) -> None:
    """One worker process: claim, run, repeat until stopped."""
    configure_logging()
    if threads:
        limit_threads(threads)
    db = Database(DB_PATH)
    worker_id = new_worker_id()
    signal.signal(signal.SIGTERM, _raise_stop)
    signal.signal(signal.SIGINT, _raise_stop)
    log.info("worker %s ready (%s threads)", worker_id, threads or "all")
    job = None
    try:
        while True:
            job = db.claim_next_job(worker_id, lease_s)
            if job is None:
                time.sleep(poll_s)
                continue
            log.info(
                "job %s video %s from %s (attempt %d)", job["id"], job["video_id"], job["from_stage"], job["attempts"]
            )
            process(db, job, worker_id, lease_s)
            job = None
    except Stop as s:
        if job is not None and db.release_job(job["id"], worker_id):
            log.info("%s: job %s queued again", s, job["id"])
        log.info("worker %s stopped", worker_id)


def main():
    ap = argparse.ArgumentParser(description="Run analysis workers.")
    ap.add_argument("--workers", type=int, default=1, help="worker processes on this machine (default 1)")
    ap.add_argument("--threads", type=int, default=None, help="compute threads per worker (default: cores / workers)")
    args = ap.parse_args()
    configure_logging()
    check_models()
    backup.back_up()
    n = max(1, args.workers)
    threads = args.threads or (max(1, (os.cpu_count() or 1) // n) if n > 1 else None)
    if n == 1:
        run_worker(threads)
        return
    ctx = mp.get_context("spawn")
    procs = [ctx.Process(target=run_worker, args=(threads,), name=f"worker-{i}") for i in range(n)]
    for p in procs:
        p.start()
    signal.signal(signal.SIGTERM, lambda *_: [p.terminate() for p in procs])  # children release their jobs
    try:
        for p in procs:
            p.join()
    except KeyboardInterrupt:  # Ctrl-C reaches the children too; wait for them to release their jobs
        for p in procs:
            p.join()


if __name__ == "__main__":
    main()
