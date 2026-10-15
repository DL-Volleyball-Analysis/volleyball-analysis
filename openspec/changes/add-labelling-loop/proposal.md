# Proposal

## Why

No model in the pipeline was trained on amateur phone footage (low corner views, wide lenses, Taiwanese halls), and
the owner will label such footage over time. Correcting the system's output is several times faster than labelling
from scratch, and every correction becomes training and test data. This loop is needed before any retraining,
including the multi-task model (change add-multitask-model).

A survey of annotation tools (2026-10-16: CVAT, Label Studio, X-AnyLabeling, the TrackNet labelling tool, Roboflow)
found that CVAT already does what we need: video tracks with keyframe interpolation, keypoint skeletons, per-frame
points, attributes, import of pre-annotations and export in standard formats, self-hosted with Docker (MIT licence).
Building our own labelling UI would be slower and harder to trust; our own code shrinks to converters that can be
tested exhaustively.

## What Changes

- CVAT, self-hosted with Docker on the owner's machine (not part of this repository; setup documented).
- `vball.datasets.cvat`: pipeline output -> CVAT pre-annotations (players as tracks with ids, the 14 court keypoints as
  a skeleton, the ball as a per-frame point with "outside" when not visible, actions as track attributes); CVAT export
  -> our dataset format (images plus per-task annotations, split by whole video). Only edited or accepted items are
  labels.
- Checks on every export: round trip of SportsMOT ground truth through both converters scores 1.0; overlays drawn
  back on sampled frames; label sanity (court keypoints fit a homography within tolerance, no ball jump beyond physics,
  at most twelve players per frame); a re-labelled subset measures the labeller's own consistency.
- Rally winners keep using the review app's existing winner override.
- Frame choice: the frames where the pipeline is least sure are exported first.

## Impact

- Specs: labelling (new).
- Code: `vball.datasets.cvat`, a script `scripts/cvat_labels.py` (export / import / check), docs/labelling.md.
- No model changes; no labelling UI in the review app.
