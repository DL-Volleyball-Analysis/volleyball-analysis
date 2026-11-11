# Single-user local deployment

Date: 2026-10-08 · Status: accepted

## Context
The users are a coach and the players of one team, reviewing their own recordings. Videos are large (1-3 GB per
match) and private; analysis needs the models and a few hours of CPU. The capstone design used Celery and Redis
for jobs, which nobody ran in practice.

## Decision
The system runs on the user's own computer: a FastAPI process, one worker process and a SQLite database in WAL mode
that holds videos, jobs, rallies, corrections and tags. The worker claims jobs with `UPDATE … RETURNING` and requeues
jobs left running after a crash. There are no accounts and no cloud services; local video files can be registered
without copying (`/videos/import`).

## Consequences
- Nothing to operate: no broker, no database server, no credentials; the data never leaves the machine.
- One machine. Several analyses run side by side (update below); more machines need the changes the update lists.
- Moving to several users would need authentication, a real job queue and object storage; the API shape (resources
  per video) does not have to change for that.

## Update 2026-11-11: several workers (change scale-out-analysis-workers)
The single worker became a limit (a weekend of matches waits in line) and was unsafe to multiply: a starting worker
requeued every running job, stealing other workers' jobs. Jobs now carry a lease (`worker_id`, `lease_until`,
`attempts`): a worker renews it from a heartbeat thread, an expired lease lets another worker take the job, a job that
lost three workers fails, and SIGTERM / Ctrl-C queue the job again at once. `python -m vball_app.worker --workers N`
runs N processes with cores / N threads each.

Measured (docs/results/scaling.md): 4 workers on 8 cores run 1.79x the jobs per hour of one, using 5.9 GB instead of
3.8 GB; a worker killed mid-job loses nothing (its job finishes on another worker with identical results). The gain is
sublinear because the stages are already multi-threaded; ball tracking and rally cues are the bottleneck stages.

Leases are the same model as a server queue's visibility timeout. Moving to several machines changes the claim to
Postgres `SELECT ... FOR UPDATE SKIP LOCKED` and the results folders to shared object storage; the API, the stage
contract and the lease rules stay as they are. A stage that hangs (rather than dies) keeps its lease; a stage timeout
is not built.

## Alternatives
- Celery + Redis, Postgres: needed for many users or machines, not for one.
- A hosted service: uploads of full matches, storage costs and privacy questions for no gain to one team.
