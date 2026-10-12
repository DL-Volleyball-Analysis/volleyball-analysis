# Proposal

## Why

The rallies stage shows demo data, so scores, the rally list and per-rally statistics are placeholders. A public
dataset now gives labelled rally boundaries on full broadcast matches (the game-state set of
masouduut94/volleyball_analytics: 8 matches, 680 rallies, serve start / serve end / rally end per rally), so a rally
detector can be built and measured. Implements [docs/prd/rally-detection.md](../../../docs/prd/rally-detection.md).

## What Changes

- `vball.rallies`: label parsing (CVAT XML), segmentation of a per-sample play probability into rallies (hysteresis,
  minimum lengths), and boundary evaluation (matched rallies, start / end error, precision / recall).
- Rally cues from the system's own signals: court visible (court keypoint confidence), ball detected and moving,
  players on court and their motion, sampled at 5 per second; a small classifier trained on the training matches.
- Baselines: a ball-track rule (no training) and the published VideoMAE game-state checkpoint.
- Scripts and a Kaggle notebook for feature extraction on the full matches; results in `docs/results/rallies.md`.
- The rallies stage uses the detector (stage version bump) only after the measurement; demo rallies stay labelled
  until then.

## Capabilities

### Modified Capabilities
- `match-scoring`: rallies are detected from the video, with a confidence, and measured against labelled boundaries.

## Impact

New `src/vball/rallies.py`, scripts, a notebook, the rallies stage in `webapp/backend/pipeline.py`. Data: the game-state
videos (3.1 GB, GPL-2.0 repository; broadcast footage, research use) stay in `data/datasets/gamestate/`, not in git.
