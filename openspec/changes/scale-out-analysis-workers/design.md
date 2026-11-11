# Design

## Context
`Database.claim_next_job` is already atomic (`UPDATE ... WHERE id = (SELECT ... LIMIT 1) RETURNING *`, SQLite in WAL
mode serialises writers). The unsafe part is recovery: `requeue_running()` at worker start assumes it is the only
worker. Stage files are written per video, and the API refuses a second active job per video, so per-video exclusivity
holds as long as a job is never run twice at once.

## Decisions

**Leases, not process tables.** Columns `worker_id TEXT`, `lease_until TEXT` (ISO time), `attempts INTEGER DEFAULT 0`.
Claim, in one statement: the oldest job that is `queued`, or `running` with `lease_until < now`; set `running`, the
worker id, `lease_until = now + LEASE_S` (default 60 s) and `attempts = attempts + 1`. A job whose attempts would exceed
`MAX_ATTEMPTS` (default 3) is set `failed` with "worker lost 3 times" in a statement before the claim. Alternatives:
recording worker PIDs and checking them (does not survive a reboot or a second machine) and a supervisor process
(one more thing to run). Leases are what Postgres-backed queues (`SKIP LOCKED` + visibility timeout) and SQS use, so
the same model carries over if the app ever leaves one machine.

**Heartbeat on a thread.** A stage can run for minutes between progress ticks, so renewal cannot rely on
`on_progress`. A daemon thread renews every `LEASE_S / 3` with `UPDATE jobs SET lease_until = ? WHERE id = ? AND
worker_id = ?`; if that updates no row, the lease was lost (the job was taken by another worker after a long stall) and
the worker abandons the job without writing its status. Only the owner writes status (`update_job` gains a `worker_id`
guard).

**Processes, not threads, for workers.** The stages are CPU-bound Python with native libraries; processes avoid the
GIL and isolate a crash. `--workers N` uses `multiprocessing` (spawn) with one `Database` per process. Each process sets
`OMP_NUM_THREADS`, `cv2.setNumThreads`, `torch.set_num_threads` and the ONNX Runtime intra-op threads to
`max(1, cores // N)` before loading models, so total threads stay near the core count.

**Stage timings in the pipeline.** `pipeline.run` measures each stage it runs with `time.perf_counter()` and returns
`{stage: seconds}` through a new `on_stage_done(stage, seconds, reused)` callback (reused stages report 0 and
`reused=True`); stage files gain `elapsed_s`. The worker stores the dict as `jobs.timings` (JSON).

**Benchmark.** `scripts/bench_workers.py --videos A B C D --from-stage players --workers 1 2 4` copies the database
and results to a temporary folder, queues the videos, runs the workers to completion and reports wall time, videos per
hour and the sum of stage times per stage. From `players` on is the realistic re-analysis case (decode and court are
cached by then) and keeps the run to minutes on CPU.

## Risks
- SQLite write contention with many workers: progress writes are throttled to 1% steps; with 4 workers the write rate
  stays far below WAL limits. Measured in the benchmark (lock wait time logged).
- A heartbeat thread hides a hung stage forever: a stage timeout is out of scope; the lease protects only against dead
  processes. Noted in the ADR.
- Memory: N workers load N copies of the models (about 1 GB each with WASB and YOLO); the benchmark reports peak RSS
  and the ADR recommends N by memory as well as cores.
