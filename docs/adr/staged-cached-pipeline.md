# Staged, versioned, cached analysis pipeline

Date: 2026-10-08 · Status: accepted

## Context
Analysing a match takes minutes to hours on a laptop CPU, and the parts improve at different speeds: a new court
model arrives while ball tracking is unchanged. The capstone web app ran everything in one call inside the API
process, so any change meant analysing again from the start, and a failure in one part lost the others. Some parts
cannot work on some footage (no court model for a view, a rally model trained on broadcasts), and the old system
showed made-up results in those cases.

## Decision
Analysis is a fixed sequence of stages (`vball.pipeline`). Each stage writes its result to `<stage>.json` in the
video's results folder with a version; a run reuses a stage whose version matches and recomputes from the first
changed or requested stage. Every stage returns `done` or `unavailable`, and `unavailable` always carries a message
saying why. The API never runs analysis: it queues a job, and a separate worker runs the pipeline.

## Consequences
- A new model reruns only its stage and the ones after it; a version bump is the explicit signal.
- Partial results survive failures, and the review app can show each stage's state and message.
- Stage results are files, easy to inspect, compare (`scripts/compare_stage_outputs.py`) and render.
- The order is fixed: a stage can only use earlier stages. Cross-stage feedback (e.g. 3D flights refining the court)
  would need a later stage, not a loop.
- Cache invalidation depends on bumping versions by hand when a stage's behaviour changes.

## Alternatives
- One function for everything (the capstone): simple, but no reuse and no partial results.
- A workflow engine (Celery, Airflow, Prefect): solves scheduling the project does not have (one machine, one
  user) and adds services to run.
