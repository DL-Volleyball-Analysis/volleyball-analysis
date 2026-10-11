# Proposal

## Why

Players are tracked but neither identified nor described: boxes show tracking ids, actions are not recognised,
and every attack tag is typed by hand. The capstone already trained an action recogniser (YOLOv11m) and a
jersey-digit detector (YOLOv8m); neither is used or measured on held-out data. Implements
[docs/prd/player-actions.md](../../../docs/prd/player-actions.md).

## What Changes

- Evaluation of both models on their test splits (Roboflow downloads), recorded before use.
- `vball.actions`: action detections assigned to player tracks and merged into events.
- `vball.jersey`: digits inside player boxes composed into numbers, voted per track.
- An `actions` pipeline stage after `players` (actions and numbers), `actions.json`, and
  `GET /videos/{id}/actions`.
- Display: numbers on boxes, the court map and the rendered video; an Actions timeline lane.
- Suggested attack / serve tags from spike and serve events, accepted or dismissed by the coach.

Out of scope: re-identification across shots. (Training new models was out of scope; the digit model is retrained
because the capstone one proved unusable, agreed 2026-10-11.)

## Capabilities

### New Capabilities
- `player-actions`: action events and shirt numbers per player track, with measured accuracy.

### Modified Capabilities
- `analysis-jobs`: the stage order gains `actions` after `players`.
- `player-stats`: suggested tags that count only once accepted.

## Impact

- `src/vball`: new `actions` and `jersey` modules; evaluation scripts in `scripts/`.
- Web app: `actions` stage and endpoint, timeline lane, number labels, suggestion review in the tag inspector.
- Models (not in git): `models/action_yolo11m.pt`, `models/jersey_digits_yolov8m.pt` from the capstone runs.
