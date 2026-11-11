# PRD: several analysis workers on one machine

Parent: [README.md](README.md) · OpenSpec: `openspec/changes/scale-out-analysis-workers/`

## Problem
One worker runs one analysis at a time ([ADR: single-user local deployment](../adr/single-user-local-deployment.md)).
A team that uploads a weekend of matches waits for them one after another, although the machine has idle cores while
a stage waits on video decoding or a single-threaded step. Running a second worker today is unsafe: at start a worker
puts every `running` job back in the queue (`Database.requeue_running`), so a second worker steals the first one's
job and both write the same results folder. Nothing records how long each stage takes, so there is no measured
answer to "where does the time go" or "what would more workers buy".

## User stories
- As a coach, I upload four matches and they are analysed side by side; a crash of one worker does not lose or
  duplicate any match.
- As the developer, I can see per stage how long it took on every job, and I can measure throughput with 1, 2 and 4
  workers on the same videos.

## Requirements
1. **Leases instead of restart recovery.** A worker that claims a job holds a lease (worker id, expiry) that it renews
   while working. Only a job whose lease has expired is taken again; a job taken too many times fails with the reason.
   Starting a worker never touches jobs other workers hold.
2. **N workers.** `python -m vball_app.worker --workers N` runs N worker processes; the compose file can scale the
   worker service. Each process limits its compute threads so N workers do not oversubscribe the CPU.
3. **One job per video stays true** under concurrency (already enforced when a job is created), so two workers never
   write one results folder.
4. **Clean stop.** On SIGTERM or Ctrl-C a worker returns its job to the queue at once instead of waiting for the lease.
5. **Stage timings.** Every job records the wall time of each stage it ran; the API returns them and the pipeline
   writes them into the stage files.
6. **Measured.** `scripts/bench_workers.py` runs the same set of videos from a chosen stage with 1, 2 and 4 workers and
   reports wall time, throughput and per-stage time; results in `docs/results/scaling.md`.

## Acceptance criteria
- A concurrency test with 4 processes claiming from 100 jobs: every job is claimed exactly once.
- A worker killed with SIGKILL mid-job: its job is finished by another worker after the lease expires, and the
  results equal a clean run's (stage files compared by `scripts/compare_stage_outputs.py`).
- The benchmark table exists with measured numbers for 1, 2 and 4 workers; the ADR states the measured speed-up and
  the bottleneck stage, whatever they are.

## Out of scope
- Several machines, a server database, object storage, accounts. The ADR describes what would change for them
  (Postgres `FOR UPDATE SKIP LOCKED` claims, shared storage for results); the API does not change.
- GPU batching across jobs.
