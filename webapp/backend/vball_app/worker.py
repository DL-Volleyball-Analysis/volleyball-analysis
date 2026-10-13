"""Analysis worker: takes queued jobs from SQLite and runs the pipeline, one at a time.

Usage: python -m vball_app.worker   (next to the API: uvicorn vball_app.main:app)
"""

import logging
import time
from pathlib import Path
from typing import Any

from vball import pipeline

from . import backup
from .db import Database
from .settings import DB_PATH, RESULTS, configure_logging
from .startup import check_models

POLL_S = 1.0
log = logging.getLogger(__name__)


def process(db: Database, job: dict) -> None:
    video = db.get_video(job["video_id"])
    if video is None:  # deleted while queued
        db.update_job(job["id"], status="failed", error="video deleted")
        return
    last: dict[str, Any] = {"stage": None, "p": 0.0}

    def on_progress(stage: str, p: float):
        # Throttle progress writes, but always record a stage change: a stage can start at the
        # same overall progress the previous one ended with.
        if stage != last["stage"] or p - last["p"] >= 0.01 or p >= 1:
            db.update_job(job["id"], stage=stage, progress=round(p, 3))
            last.update(stage=stage, p=p)

    try:
        out = pipeline.run(
            Path(video["path"]),
            RESULTS / video["id"],
            job["from_stage"],
            on_progress,
            court_corrections=lambda: db.court_corrections(video["id"]),
        )
        r = out.get("rallies") or {}
        if r.get("status") == "done":  # detected rallies replace demo or earlier ones; corrections move along
            db.replace_detected_rallies(video["id"], r.get("rallies", []))
        db.update_job(job["id"], status="done", stage=None, progress=1.0)
        backup.back_up_if_due()
    except Exception as e:
        log.exception("job %s failed", job["id"])
        db.update_job(job["id"], status="failed", error=f"{type(e).__name__}: {e}"[:500])


def main():
    configure_logging()
    check_models()
    db = Database(DB_PATH)
    backup.back_up()
    if n := db.requeue_running():
        log.info("requeued %d interrupted job(s)", n)
    log.info("worker ready")
    while True:
        job = db.claim_next_job()
        if job is None:
            time.sleep(POLL_S)
            continue
        log.info("job %s video %s from %s", job["id"], job["video_id"], job["from_stage"])
        process(db, job)


if __name__ == "__main__":
    main()
