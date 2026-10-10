# Design

## Context

- Baseline (docs/results/player-tracking.md): YOLO26s 960 px + BoT-SORT at 10 fps; SportsMOT volleyball val
  IDF1 0.484, HOTA 0.467, precision 0.614, recall 0.875; oracle on-court filter 0.622.
- SportsMOT: 15 volleyball train and 15 val sequences with labels; labels contain only players on court.
  Licence CC BY-NC 4.0: research use, never redistributed (private Kaggle dataset only).
- `place_on_court` drops people outside the court plus margins, only in shots with an ok court.

## Goals / Non-Goals

**Goals:** fewer boxes on non-players, measured on labels; a filter that also works without a court.
**Non-Goals:** identity across cuts, jersey identity, a new tracker.

## Decisions

### Fine-tune, single class, same input size
`scripts/build_sportsmot_detection.py` turns the 15 training sequences into a YOLO detection set (one class,
every 3rd frame: consecutive frames are near duplicates), split by sequence into train / valid (13 / 2); the 15
val sequences stay untouched for the tracking evaluation. YOLO26s from the COCO weights, 960 px, on Kaggle
(`notebooks/train_player_detector.ipynb`, same Colab/Kaggle pattern as the digit notebook). Evaluation reuses
`scripts/eval_player_tracking.py` with the new weights.

### Cap
After tracking and placement, per frame: placed players first, then by confidence, at most 12. Applied to the
stored table so every consumer sees the same players.

### Team and role
`vball.teams`: per track, sample up to 10 non-interpolated boxes, take the torso crop (upper middle of the box)
and compute an HSV colour histogram (cheap, no new model). k-means with k = 2 on track histograms; a track is
`other` when its distance to the nearest centre exceeds a threshold set from the within-team spread (e.g. 2.5
median absolute deviations). If colour proves too weak (measured: share of SportsMOT val referee tracks caught,
using unmatched tracks against the labels), switch the embedding to SigLIP as in the Roboflow pipelines.
The `team` column replaces the side of the net as team identity when the clustering is confident; side stays as
the court-derived fallback.

### Measuring the role check
SportsMOT labels only players, so a predicted track that matches no labelled track is a non-player. Report how
many such tracks the role check marks `other`, and how many labelled players it wrongly marks `other`.

## Risks / Trade-offs

- [Broadcast-only training data] → our own gym footage may differ; the cap and role check do not depend on the
  detector, and the five clips are checked by eye.
- [Teams in similar colours] → clustering is marked not confident and no track is marked `other` from colour alone.
- [Licence] → SportsMOT stays private on Kaggle; weights trained on it are for research use.
