# Proposal

## Why
Rally detection does not work on fixed cameras (trained on broadcast), and there are no labels for fixed-camera rallies
or point winners. The matches' score bug gives both for free (PRD docs/prd/score-labels.md).

## What Changes
- `vball.scorebug`: read the score bug (crop, Tesseract, pattern "(s) pp-pp (s)"), clean the sequence (points move by
  one, sets reset), return point changes with time and scoring team.
- `scripts/label_rallies.py`: labels per match (rally ends, point winners) to `data/datasets/watchdog/labels/`.
- Eight full matches downloaded (720p, local only) to `data/datasets/watchdog/videos/`.
- Then: rally cues from pipeline results and a fixed-camera rally model, evaluated by match (a follow-up task list in
  this change once the labels exist).

## Capabilities

### Modified Capabilities
- `match-scoring`: point labels read from the on-screen score.

## Impact
New `src/vball/scorebug.py`, `scripts/label_rallies.py`, tests; pytesseract in requirements (Tesseract binary needed
locally; tests skip without it). No change to the pipeline yet.
