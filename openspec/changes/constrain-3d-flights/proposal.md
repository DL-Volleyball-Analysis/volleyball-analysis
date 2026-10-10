# Proposal

## Why

The 3D stage is accurate on clean synthetic rallies but keeps no flight on real footage: false and missed ball
detections cut flights into mixed pieces, and the unconstrained fit then prefers a ball just in front of the
camera (diagnosis in docs/research/directions.md section 1). Short attacks are ambiguous along the line of sight
even when clean. Using what the system already knows (hall, floor, players at the touches) is both the fix and
the project's research contribution. Implements [docs/prd/constrained-3d.md](../../../docs/prd/constrained-3d.md).

## What Changes

- Synthetic rallies with realistic detection errors (missed, false, noisy) for testing and the ablation.
- Robust flights: drop detections inconsistent with a flight and refit.
- A bounded fit: inside the hall, above the floor, speed limit; ending on a bound means low quality.
- Player-anchored touches: a prior pulling a flight's first / last position toward the nearest player on court.
- An ablation and a real-footage report in docs/results/trajectory.md.

Out of scope: a learned uplifting baseline and two-camera ground truth (later changes); 2D detector work.

## Capabilities

### New Capabilities

### Modified Capabilities
- `ball-trajectory-3d`: robust, bounded and player-anchored fitting (new requirements; archived after
  `add-ball-trajectory-3d`).

## Impact

- `src/vball/trajectory/` (fit, segmentation, synthetic errors), `scripts/eval_trajectory_synthetic.py`.
- Web app trajectory stage (reads players.csv.gz for anchors), stage version; tactics board shows anchored flights.
