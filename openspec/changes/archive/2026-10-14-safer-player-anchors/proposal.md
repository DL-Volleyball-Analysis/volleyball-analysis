# Proposal

## Why
Player anchors pick the wrong player when several stand near the ball's ray, and a wrong anchor makes a flight far
worse than no anchor (attack 0.76 -> 3.9 m in the stress test). The pipeline offers every placed player as a candidate
(PRD docs/prd/constrained-3d.md, addendum 2026-10-13).

## What Changes
- `FlightConfig.anchor_margin_m` (default 1.0): a touch is anchored only when the nearest player to the ray is nearer
  than the second-nearest by at least the margin.
- Trajectory stage version 6; real clips re-run, flights before and after recorded.
- The stress test reports the default and 0.5 m.

Out of scope: choosing the toucher from the action stage (needs real 3D ground truth to measure).

## Capabilities

### Modified Capabilities
- `ball-trajectory-3d`: anchors require an unambiguous toucher.

## Impact
`src/vball/trajectory/__init__.py`, `src/vball/pipeline/__init__.py` (version), tests, the synthetic evaluation script,
docs/results/trajectory.md, papers and public claims of the anchor gain.
