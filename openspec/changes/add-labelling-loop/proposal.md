# Proposal

## Why

No model in the pipeline was trained on amateur phone footage (low corner views, wide lenses, Taiwanese halls), and
the owner will label such footage over time. Correcting the system's output is several times faster than labelling
from scratch, and every correction becomes training and test data. This loop is needed before any retraining,
including the multi-task model (change add-multitask-model).

## What Changes

- Review app: a labelling mode on sampled frames of an analysed video, prefilled from the pipeline: court points
  (the 14 keypoints), ball position or "not visible", player boxes with ids, action per player, rally winner per rally.
  Accept, move, add, delete; a frame may be labelled for any subset of tasks.
- Backend: labels stored per video and frame with the task, the user and the time; never overwritten, a new version
  supersedes; the app database backup covers them.
- `vball.datasets.labels`: export to one dataset format (images plus per-task annotations, a split by video) that the
  public datasets are also converted into.
- Frame choice: frames where the pipeline is least sure first (low court status, missed ball, crowded players).
- A label count per task and per video in the app.

## Impact

- Specs: labelling (new).
- Code: webapp backend (labels API and table), frontend (labelling mode), `vball.datasets.labels`.
- No model changes.
