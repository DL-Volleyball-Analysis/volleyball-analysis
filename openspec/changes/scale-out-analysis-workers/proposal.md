# Proposal

## Why

The app runs one analysis at a time, and running a second worker is unsafe: a starting worker requeues every running
job, so it steals the other worker's job and both write one results folder. There is also no record of how long each
stage takes, so throughput questions have no measured answer (PRD `docs/prd/scale-out-workers.md`).

## What Changes

- Jobs get a lease: `worker_id`, `lease_until`, `attempts`. Claiming takes the oldest queued job or a running job whose
  lease has expired, in one `UPDATE ... RETURNING`; a heartbeat thread renews the lease; a job past the attempt limit
  fails with "worker lost N times". **BREAKING** for the worker's start-up behaviour: `requeue_running` is removed.
- `python -m vball_app.worker --workers N` starts N processes, each with its own worker id and a thread limit for
  OpenCV, ONNX Runtime and PyTorch; SIGTERM and SIGINT release the current job.
- Stage timings: `vball.pipeline.run` measures each stage and passes the times to the caller and the stage file;
  the jobs table stores them as JSON; the job endpoints (`/videos/{id}/jobs/latest`, the job stream) return them.
- `scripts/bench_workers.py` and `docs/results/scaling.md`; the deployment ADR records the decision and the numbers.

## Capabilities

### New Capabilities
(none)

### Modified Capabilities
- `analysis-jobs`: recovery by leases instead of at worker start; several workers; stage timings.

## Impact

- Code: `webapp/backend/vball_app/{db,worker,schemas}.py`, `src/vball/pipeline/__init__.py`,
  `docker-compose.yml`, new `scripts/bench_workers.py`, backend and pipeline tests.
- Database: three columns and one JSON column added to `jobs` by the existing start-up migration (no data lost).
- Docs: ADR `single-user-local-deployment` (updated), `docs/architecture.md`, `docs/results/scaling.md`.
