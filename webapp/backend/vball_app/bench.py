"""Throughput of several analysis workers on one machine (change scale-out-analysis-workers).

Each run gets a fresh data folder (database and results), so nothing is reused between runs and the app's own data
is never touched. Every video is registered `copies` times (separate results folders, as different uploads would be),
one job each, then `python -m vball_app.worker --workers N` runs until every job has finished. With `kill_after_s`
one worker process is killed with SIGKILL at that time, to show its job being finished by another worker once the
lease runs out.
"""

import json
import os
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import psutil

from vball.pipeline.stages.decode import video_meta

from .db import FINISHED, Database


def run(
    videos: list[Path],
    workers: int,
    copies: int = 1,
    from_stage: str = "decode",
    lease_s: float = 20.0,
    kill_after_s: float | None = None,
    keep: Path | None = None,
) -> dict:
    data = Path(tempfile.mkdtemp(prefix=f"vball_bench_{workers}w_", dir=keep))
    db = Database(data / "webapp.db")
    jobs = []
    for v in videos:
        meta = video_meta(v)
        for k in range(copies):
            vid = db.add_video(f"{v.stem}#{k}", str(v.resolve()), meta)["id"]
            jobs.append(db.add_job(vid, from_stage)["id"])
    env = {**os.environ, "VBALL_WEBAPP_DATA": str(data)}
    cmd = [sys.executable, "-m", "vball_app.worker", "--workers", str(workers), "--lease", str(lease_s)]
    t0 = time.perf_counter()
    proc = subprocess.Popen(cmd, env=env, stdout=subprocess.DEVNULL, stderr=open(data / "worker.log", "w"))
    root = psutil.Process(proc.pid)
    peak_rss, killed = 0, None
    try:
        while True:
            tree = [root, *root.children(recursive=True)]
            rss = 0
            for p in tree:
                try:
                    rss += p.memory_info().rss
                except psutil.NoSuchProcess:
                    pass
            peak_rss = max(peak_rss, rss)
            if kill_after_s is not None and killed is None and time.perf_counter() - t0 >= kill_after_s:
                kids = root.children() or [root]
                killed = kids[0].pid
                os.kill(killed, signal.SIGKILL)
            states = [s for j in jobs if (s := db.get_job(j)) is not None]
            if all(s["status"] in FINISHED for s in states):
                break
            time.sleep(1.0)
        wall = time.perf_counter() - t0
    finally:
        proc.send_signal(signal.SIGTERM)
        try:
            proc.wait(30)
        except subprocess.TimeoutExpired:
            proc.kill()
    per_stage: dict[str, float] = {}
    for s in states:
        for stage, sec in (s["timings"] or {}).items():
            per_stage[stage] = per_stage.get(stage, 0.0) + sec
    return {
        "workers": workers,
        "jobs": len(jobs),
        "done": sum(s["status"] == "done" for s in states),
        "failed": [s["error"] for s in states if s["status"] == "failed"],
        "attempts": sorted(s["attempts"] for s in states),
        "wall_s": round(wall, 1),
        "jobs_per_hour": round(len(jobs) / wall * 3600, 1),
        "stage_s": {k: round(v, 1) for k, v in sorted(per_stage.items(), key=lambda kv: -kv[1])},
        "peak_rss_gb": round(peak_rss / 1e9, 2),
        "killed_pid": killed,
        "data": str(data),
    }


def to_json(results: list[dict]) -> str:
    return json.dumps(results, indent=2)
