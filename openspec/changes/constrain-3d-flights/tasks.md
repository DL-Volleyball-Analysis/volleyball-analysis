# Tasks

## 1. Realistic synthetic errors

- [x] 1.1 Add `synthetic.corrupt` (bursty misses, false points, noise) and synthetic players at the touches; verify tests that the rates are respected
- [x] 1.2 Measure miss and false rates on the evaluation clips' ball tracks and record them in docs/results/trajectory.md

## 2. Fit

- [x] 2.1 Robust refit (drop by residual, refit, report dropped); verify the false-detection scenario test
- [x] 2.2 Bounded fit (hall box, floor, speed) with "on a bound" quality; verify the near-camera scenario test
- [x] 2.3 Player anchors (nearest player to the ray at the ends, soft prior, reported anchors); verify the short-attack and no-players scenario tests

## 3. Evaluation

- [x] 3.1 Extend `scripts/eval_trajectory_synthetic.py` with the ablation (none, bounds, + robust, + anchors) per flight type on corrupted rallies; record the table
- [x] 3.2 Real-clip report: flights segmented, kept, low quality, residuals, anchors per clip; record it

## 4. Web app

- [x] 4.1 Trajectory stage passes player positions, stores dropped / anchors / bound reasons; bump the version; verify backend tests
- [x] 4.2 Tactics board shows anchored ends and the reasons; verify component tests; re-render the evaluation clip

## 5. Docs

- [ ] 5.1 Update docs/results/trajectory.md, README status and the papers' 3D section; `openspec validate constrain-3d-flights --strict`
