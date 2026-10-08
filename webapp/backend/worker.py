"""Analysis worker: takes queued jobs from SQLite and runs the pipeline, one at a time.

Usage: python backend/worker.py   (next to the API: uvicorn --app-dir backend main:app)
"""
import time
import traceback
from pathlib import Path

import pipeline
from database import Database
from settings import DB_PATH, RESULTS

POLL_S = 1.0


def process(db: Database, job: dict) -> None:
    video = db.get_video(job["video_id"])
    if video is None:  # deleted while queued
        db.update_job(job["id"], status="failed", error="video deleted")
        return
    last = {"stage": None, "p": 0.0}

    def on_progress(stage: str, p: float):
        # Throttle progress writes, but always record a stage change: a stage can start at the
        # same overall progress the previous one ended with.
        if stage != last["stage"] or p - last["p"] >= 0.01 or p >= 1:
            db.update_job(job["id"], stage=stage, progress=round(p, 3))
            last.update(stage=stage, p=p)

    try:
        pipeline.run(Path(video["path"]), RESULTS / video["id"], job["from_stage"], on_progress)
        db.update_job(job["id"], status="done", stage=None, progress=1.0)
    except Exception as e:
        traceback.print_exc()
        db.update_job(job["id"], status="failed", error=f"{type(e).__name__}: {e}"[:500])


def main():
    db = Database(DB_PATH)
    if n := db.requeue_running():
        print(f"requeued {n} interrupted job(s)", flush=True)
    print("worker ready", flush=True)
    while True:
        job = db.claim_next_job()
        if job is None:
            time.sleep(POLL_S)
            continue
        print(f"job {job['id']} video {job['video_id']} from {job['from_stage']}", flush=True)
        process(db, job)


if __name__ == "__main__":
    main()
