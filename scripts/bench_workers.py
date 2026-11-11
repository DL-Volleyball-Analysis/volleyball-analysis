"""Measure analysis throughput with 1, 2 and 4 workers on the same videos (change scale-out-analysis-workers).

  .venv/bin/python scripts/bench_workers.py data/videos/broadcast_*.mp4 --copies 2 --workers 1 2 4
  .venv/bin/python scripts/bench_workers.py data/videos/broadcast_side_rally.mp4 --copies 4 --workers 2 --kill-after 40

Each run uses its own fresh data folder (vball_app.bench); the app's database is never touched.
"""

import argparse
from pathlib import Path

from vball_app import bench


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("videos", nargs="+", type=Path)
    ap.add_argument("--copies", type=int, default=1, help="jobs per video (separate uploads)")
    ap.add_argument("--workers", type=int, nargs="+", default=[1, 2, 4])
    ap.add_argument("--from-stage", default="decode")
    ap.add_argument("--lease", type=float, default=20.0)
    ap.add_argument("--kill-after", type=float, default=None, help="SIGKILL one worker after this many seconds")
    ap.add_argument("--out", type=Path, default=None, help="write the results as JSON")
    args = ap.parse_args()
    results = []
    for n in args.workers:
        r = bench.run(args.videos, n, args.copies, args.from_stage, args.lease, args.kill_after)
        results.append(r)
        print(
            f"{n} worker(s): {r['done']}/{r['jobs']} done in {r['wall_s']} s ({r['jobs_per_hour']} jobs/h), "
            f"peak memory {r['peak_rss_gb']} GB, attempts {r['attempts']}, failed {r['failed'] or 'none'}",
            flush=True,
        )
        print(f"  stage time: {r['stage_s']}", flush=True)
    if args.out:
        args.out.write_text(bench.to_json(results))


if __name__ == "__main__":
    main()
