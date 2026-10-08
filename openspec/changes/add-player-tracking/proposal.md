# Proposal

## Why

Nothing in the analysis knows where the players are, yet the tactics board, attack efficiency and touch detection all need it. The capstone's player tracker was never measured and is gone from the new pipeline. Implements [docs/prd/player-tracking.md](../../../docs/prd/player-tracking.md).

## What Changes

- New `players` pipeline stage between `ball` and `events`: person detection and multi-object tracking with ids that hold through a rally.
- On-court filtering and court positions (metres, side of net) when a court mapping exists; detections and tracks without it, with positions marked unavailable.
- Player data served to the web app per time window (like ball data) and drawn as an optional video overlay layer.
- An evaluation script reporting HOTA, IDF1, MOTA and detection recall / precision on labelled volleyball sequences (SportsMOT volleyball split, later our own clips).
- Baseline first with a pretrained detector and the built-in tracker; a Colab fine-tuning notebook only if the baseline misses the PRD targets.

Out of scope: identity across rallies, jersey numbers, pose and action recognition, the 2D tactics board view (separate change).

## Capabilities

### New Capabilities
- `player-tracking`: on-court players per frame with stable ids within a rally, court positions and measured accuracy.

### Modified Capabilities
- `analysis-jobs`: the stage order gains `players` between `ball` and `events`.

## Impact

- `src/vball`: new player detection / tracking module and evaluation script in `scripts/`.
- Web app: `players` stage, `GET /videos/{id}/players?start=&end=`, overlay layer and a "Players" toggle.
- Models: pretrained YOLO26 person weights (downloaded by ultralytics); optionally a fine-tuned checkpoint from Colab.
- Data: SportsMOT volleyball split (CC BY-NC 4.0, research use) in `data/datasets/`, not committed.
