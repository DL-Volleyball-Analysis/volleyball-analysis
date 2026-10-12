# Evaluation by match

Date: 2026-10-08 · Status: accepted

## Context
Consecutive video frames are nearly identical, and the same match shares players, shirts, lighting and camera.
A random split of frames puts near-copies of the test frames into training, so scores look far better than the
system is on a new match. The capstone's action detector was measured that way (test mAP@0.5 0.957 on the same
matches as training); on unseen matches its macro F1 was 0.303 (docs/results/actions.md).

## Decision
Every training and test split in this project is by match (or by video for SportsMOT): no match contributes to
both. Thresholds and other settings are chosen on the training matches only, by leave-one-match-out where there is
no separate validation set (e.g. the fixed-camera rally model). A metric without labels is reported as a proxy or as
not measured, never as accuracy; each number in docs/results/ says which kind it is.

## Consequences
- Scores are lower and honest; they predict what a coach sees on a new recording.
- Small datasets give few matches per split, so results carry wide uncertainty and are reported per match.
- Arenas can still repeat across matches (the fixed-camera clips share arenas with the training matches); such
  overlap is stated next to the result.

## Alternatives
- Random frame splits: the default in many tutorials, and the cause of the capstone's inflated action score.
- Cross-validation over frames: the same leak, repeated.
