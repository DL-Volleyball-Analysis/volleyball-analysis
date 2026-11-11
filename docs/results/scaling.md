# Several analysis workers on one machine (2026-11-11)

Change `scale-out-analysis-workers`. Measured with `scripts/bench_workers.py` (fresh data folder per run, the app's
database untouched) on the development machine: Apple Silicon, 8 cores, 16 GB, CPU only.

## Throughput
Eight jobs: four broadcast clips (5-8 s, 1080p) registered twice each, full analysis from `decode`. Threads per worker:
cores / workers. Raw numbers in `outputs/bench/workers.json`.

| Workers | Wall time | Jobs per hour | Speed-up | Sum of stage times | Peak memory |
|---|---|---|---|---|---|
| 1 | 671 s | 42.9 | 1.00x | 669 s | 3.8 GB |
| 2 | 493 s | 58.4 | 1.36x | 977 s | 4.2 GB |
| 4 | 375 s | 76.9 | 1.79x | 1379 s | 5.9 GB |

- Four workers finish the same work 1.79x faster. The gain is well below 4x because the stages already use several
  cores each (ONNX Runtime, PyTorch, OpenCV): the sum of stage times doubles from 1 to 4 workers, so the cores were
  partly busy before. What a second worker adds is filling the gaps of single-threaded steps (video decoding, Python
  linking and fitting).
- Where the time goes (1 worker, share of stage time): ball 27%, rallies 25% (cues sampled over the whole clip), players
  14%, court 14%, actions 13%, trajectory 4%, decode 3%. Ball and rallies are the stages to make faster next; more
  workers do not.
- Memory grows by about 0.7 GB per extra worker (each loads its own models). On 16 GB, four workers leave room; the
  ADR recommends choosing N by memory as well as by cores.

## Recovery
Three jobs, two workers, lease 20 s; 40 s in, the process holding a job was killed with SIGKILL
(`--kill-after 40`, `outputs/bench/kill.json`). All three jobs finished, the killed one on its second attempt by the
other worker after its lease expired (attempts 1, 1, 2), in 276 s. Its stage files are identical to a clean run's
(`scripts/compare_stage_outputs.py`, `ball_raw` scratch folder excluded).

## Tests
`webapp/backend/tests/test_workers.py`: four processes claiming from 100 jobs take each exactly once; a second worker
starting leaves a held job alone; an expired lease is taken over and the old holder's late writes are refused; a job
that lost three workers fails with the reason; SIGTERM and SIGINT queue the job again without counting an attempt;
stage timings skip reused stages.
