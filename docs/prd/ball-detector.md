# Training a volleyball ball detector for broadcast and gym footage

Version 1.0 · 2026-10-11 · Owner: YuJia Liang · Parent: [ball-tracking.md](ball-tracking.md)

## Why
- Labelled evaluation (docs/results/ball-tracking.md) shows the ball detectors we use do not transfer: VballNet V4c
  reaches F1 0.275 at 4 px on the Volleyball dataset's broadcast test matches; its own 0.902 was measured on beach
  volleyball. The 2D ball track is the bottleneck of the 3D stage and limits the ball prior of action attribution
  (0.678 with labelled balls, 0.670 with detected ones).
- Enough public labelled ball data now exists to train for the two kinds of footage the system targets: broadcast
  (the Volleyball dataset) and amateur gym recordings (volleyball-orel.ru, Volleylitics).

## Data (found 2026-10-11)
| Source | Footage | Ball labels | Licence | Use |
|---|---|---|---|---|
| Volleyball dataset (Ibrahim et al., CVPR 2016) + Perez et al. ball annotations | 55 broadcast matches, 720p | every frame of 4,830 clips x 41 | research use | train (train + validation matches), test (official 16) |
| volleyball-orel.ru `data_20250711_2330` (VballNet author) | Russian regional league, indoor gyms, side and backline views | per-frame CSV per video | not stated: research use only, not redistributed | train / held-out matches |
| Volleylitics ball detection v8 (Roboflow, HF GYdevy/volleyball-big-ds) | indoor amateur matches | 22,038 images, boxes | MIT | frame-level auxiliary data; sequences only where file names give match / rally / frame |
| VolliQ (Kaggle) | one indoor match, 4 synchronised cameras, 1080p | 10,550 boxes, partly model-generated | CC BY-NC-SA 4.0 | not for training; candidate for multi-view 3D checks (sync lag ~79 ms) |
| beach-volley-vision, VballNet beach clips | beach | small | MIT | out of domain, not used |
| WASB published weights (BMVC 2023) | trained on the Volleyball dataset | — | MIT | initialisation and in-domain reference |

## What
1. A training pipeline in `training/ball/` for WASB's HRNet (3 RGB frames in, 3 heatmaps out), starting from WASB's
   Volleyball-dataset weights, on a mix of broadcast and gym clips; runs on Kaggle.
2. A dataset builder that turns each source into one clip format (frames + per-frame ball position or none).
3. Evaluation with `scripts/eval_ball_detection.py` on: the Volleyball test matches, held-out orel matches, and our own
   evaluation clips (proxy and contact sheets, since they have no labels).
4. If the trained model beats the current detector, it becomes the pipeline's ball model (stage version bump), and the
   3D and action results are re-measured with it.

## Research question
Does adding amateur gym footage to broadcast training data give one detector that works on both, or does each kind
need its own model? Reported as a matrix: training mix x test set.

## Success
- On the Volleyball test matches: no worse than WASB's published weights with our evaluation.
- On held-out gym matches: a clear gain over WASB's weights and over VballNet.
- Every number with its split; no tuning on test matches.

## Out of scope
Our own labelling (a later change if the public data proves insufficient for our clips); multi-view 3D ground truth.
