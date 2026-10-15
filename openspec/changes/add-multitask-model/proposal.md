# Proposal

## Why

Four separate models (court keypoints, players, ball, actions) each learned from one public dataset. A shared backbone
with one head per task can learn from all of them and from the owner's own labels at once (losses masked per task),
and runs one backbone instead of four. It depends on the labelling loop (change add-labelling-loop) for amateur
training and test data.

## What Changes

- `training/multitask/`: a network with a shared backbone (YOLO26-size) and heads for player boxes, the 14 court
  keypoints and the ball (heatmap from three consecutive frames); action, re-identification and rally-winner heads
  come later; per-task loss masks; notebook for Kaggle or Colab.
- Dataset from `vball.datasets.labels` (public datasets plus own labels, split by video).
- Evaluation per head against the current single-task model on the same held-out test sets, plus held-out amateur
  footage, and CPU time per frame.
- `vball.pipeline.models`: a multi-task adapter that serves each adopted head; heads that lose keep the single-task
  model. Stage versions bump for the stages whose model changes.

## Impact

- Specs: multitask-model (new).
- Code: training/multitask, vball.pipeline.models, evaluation scripts; models/manifest.json.
- Depends on: add-labelling-loop (dataset format and amateur test videos).
