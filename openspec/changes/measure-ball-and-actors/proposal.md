# Proposal

## Why

Ball tracking and action recognition were judged without labels. A look at the ball detections showed many
false ones and a tiny ball the detector misses, and the action model often names the wrong player. A public
dataset has both kinds of labels (the Volleyball dataset with ball annotations and per-player action labels), so
each change can now be measured before it enters the pipeline. Implements
[docs/prd/ball-and-actors.md](../../../docs/prd/ball-and-actors.md).

## What Changes

- `vball.ball_detect`: candidate detectors (VballNet whole frame / tiles, RAVEL-VB 011 / 012).
- `vball.ball_track`: fixed-object check with camera compensation, Viterbi linking, short-gap filling.
- `scripts/eval_ball_detection.py` + Kaggle notebook: precision / recall / F1 at 4 and 10 px on the test split.
- `vball.actors`: per-player action scores combined over frames and weighted by the distance to the ball.
- `scripts/eval_actions_volleyball.py` + Kaggle notebook: macro F1 per player, tuned on validation, reported on test.
- The pipeline adopts the best ball method and the actor weighting only when they beat the current ones.

## Capabilities

### Modified Capabilities
- `ball-tracking`: measured on labelled frames; candidate detectors and a tracker.
- `player-actions`: the acting player is weighted by the ball's position.

## Impact

New modules in `src/vball/`, two scripts, two Kaggle notebooks, results in `docs/results/ball-tracking.md` and
`docs/results/actions.md`. The pipeline's ball stage version changes if its method changes.
