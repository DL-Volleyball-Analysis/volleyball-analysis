# Design

## Decisions

**Masked multi-task loss.** Each sample carries the tasks it is labelled for; the loss sums only those heads, weighted
per task (uncertainty weighting or fixed weights tuned on validation). Batches mix datasets so every head sees data
each step.

**Ball from three frames.** The ball head takes features of frames t-1, t, t+1 (stacked input or temporal fusion at the
neck), following TrackNet/WASB; if it stays below WASB on the gym test, the pipeline keeps WASB for the ball.

**One resolution.** 960 px input as the player detector and court v2 use; the court head predicts keypoints as a pose
head does; players as boxes.

**Adoption per head.** A head replaces its single-task model only when it is at least as good on that task's existing
held-out test (SportsMOT val IDF1/HOTA, court error in metres on gym and broadcast tests, ball F1 at 10 px, action
macro F1) and on the amateur test videos. Partial adoption is the expected first outcome.

## Risks
- Negative transfer between tasks; mitigated by per-task weights and by keeping single-task models when a head loses.
- Kaggle weekly GPU quota limits the number of training runs.
