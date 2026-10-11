# Proposal

## Why

The ball detectors the system uses were trained on other footage (VballNet's reported F1 0.902 is on beach
volleyball) and reach F1 0.275 at 4 px on labelled broadcast matches. The 2D ball track limits the 3D stage and the
ball prior of action attribution. Public labelled ball data now covers broadcast and amateur gym footage, so a
detector can be trained for the system's own targets. Implements [docs/prd/ball-detector.md](../../../docs/prd/ball-detector.md).

## What Changes

- `scripts/build_ball_clips.py`: one clip format (frames + per-frame ball or none) from the Volleyball dataset, the
  orel gym videos and Volleylitics sequences, with splits by match.
- `training/ball/`: training of WASB's HRNet from its Volleyball-dataset weights on a broadcast + gym mix, with
  checkpoints and resume; a Kaggle notebook.
- Evaluation of the trained model, WASB's weights and VballNet on the Volleyball test matches, held-out gym matches
  and our evaluation clips; results in `docs/results/ball-tracking.md`.
- The pipeline's ball stage switches to the trained model only if it wins (stage version bump); 3D and actions
  re-measured.

## Capabilities

### Modified Capabilities
- `ball-tracking`: the ball model is trained for broadcast and gym footage and measured on held-out matches of both.

## Impact

New `training/ball/`, `scripts/build_ball_clips.py`, a notebook, `vball.ball_detect.Wasb` weights path; data under
`data/datasets/` (not in git). WASB code (MIT) is cloned at run time, not copied into the repo.
