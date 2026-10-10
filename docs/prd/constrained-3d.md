# PRD: 3D ball flights that hold up on real footage

Parent: [README.md](README.md) · OpenSpec: `openspec/changes/constrain-3d-flights/` · Research: [../research/directions.md](../research/directions.md)

## Problem
The 3D stage is accurate on clean synthetic rallies (0.05 m on a serve) but produces no usable flight on real
footage: on the one evaluation clip with a good calibration, every fitted flight was physically impossible and
dropped. The diagnosis (research/directions.md section 1): false and missed ball detections cut flights into short
mixed pieces (residuals 20-128 px), and the unconstrained fit then prefers a near, slow ball in front of the
camera to a far, fast one. Short attacks are ambiguous along the line of sight even with a clean track.

This is also the research core of the project: single-camera 3D ball trajectories for volleyball, using what
the rest of the system knows (court, net, players) to remove the depth ambiguity.

## User stories
- As a coach, the tactics board shows real flights from my video, each marked reliable or uncertain.
- As a researcher, I can state how much each constraint (bounds, player anchors, outlier removal) improves 3D
  accuracy, measured on synthetic rallies with realistic detection errors, and how many real flights survive.

## Requirements
1. Realistic synthetic tests: rallies rendered with missed detections, false detections and detection noise at
   rates measured on our clips.
2. A bounded fit: every flight stays inside the hall and above the floor, with a speed limit; a fit that ends on
   a bound is low quality.
3. Robust flights: detections inconsistent with a flight are dropped and the flight refitted, before quality is
   judged.
4. Player-anchored touches: where player court positions are known at a flight's first or last frame, the ball
   there is pulled toward the nearest player (horizontal distance prior); each flight says whether it was anchored.
5. Measured gains: an ablation on synthetic rallies (none, bounds, + robust, + anchors) and the share of real
   flights kept and plausible per clip, in `docs/results/trajectory.md`.

## Acceptance criteria
- Synthetic rallies with 10% false and 30% missed detections: median 3D error of serves, sets and receptions
  within 0.3 m, and attacks better than without anchors (target: half the error).
- Real evaluation clip with an ok calibration: at least half of the segmented flights kept and plausible, and
  drawn on the tactics board with their quality.

## Out of scope
- A learned uplifting model (*Where Is The Ball*, CVPRW 2025) as a baseline: a later change, trained on the same
  simulator. Two-camera ground truth: a later change (needs footage).
- Better 2D ball detection (change `measure-ball-2d`).

## Dependencies
- `add-ball-trajectory-3d` (fit, stage, board), `add-player-tracking` (court positions of players).
