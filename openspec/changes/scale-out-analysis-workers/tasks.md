# Tasks

## 1. Leases
- [ ] 1.1 Jobs columns `worker_id`, `lease_until`, `attempts`, `timings` via the start-up migration; claim with lease
  and expired-lease reclaim; attempt limit; owner-guarded `update_job`; remove `requeue_running`; tests (concurrent
  claims from 4 processes, expired lease, attempt limit, second worker start)
- [ ] 1.2 Heartbeat thread and lost-lease abandon; SIGTERM / SIGINT release; tests

## 2. Several workers
- [ ] 2.1 `--workers N`, worker ids, per-process thread limits; compose scaling note; SIGKILL test with two workers
  (job finished by the other, stage outputs equal)

## 3. Stage timings
- [ ] 3.1 `pipeline.run` callback and `elapsed_s` in stage files; jobs.timings; `GET /jobs/{id}` returns them; schema
  and frontend types regenerated; tests

## 4. Measure and document
- [ ] 4.1 `scripts/bench_workers.py`; run 1, 2, 4 workers on four cached videos from `players`; `docs/results/scaling.md`
- [ ] 4.2 ADR and architecture updated with the measured speed-up, bottleneck stage and memory; CHANGELOG;
  `openspec validate scale-out-analysis-workers --strict`
