# Design

## Data and split
Game-state set (masouduut94/volleyball_analytics): 8 broadcast matches (1080p, 25-30 fps) with CVAT frame tags
serving-start, serving-end, in-game-end for each rally (680 rallies). Two recording batches (April and October 2023).
Split by match: test = 6 (April, 42 rallies) and 9 (October, 179); validation = 3 and 10; train = 2, 4, 8, 13.
A labelled rally runs from serving-start to in-game-end.

## Cues (sampled at 5 per second)
- court: the best court keypoint confidence and whether a plausible court is fitted (wide view vs close-up / replay);
- ball: detected share and median speed in the surrounding second;
- players: number of player boxes, number on court (with a court), mean box motion.
Each is computed by the existing modules; a gradient-boosted classifier (scikit-learn) maps a window of cues to
P(play). No video model is trained.

## Segmentation
Hysteresis on the smoothed P(play): open at p_on, close at p_off, drop rallies shorter than min_rally_s, merge gaps
shorter than min_gap_s. Chosen on validation.

## Evaluation
A detected rally matches a labelled one when their temporal IoU is at least 0.5 (one-to-one, greedy by IoU).
Reported: precision, recall, median |start error|, median |end error|; also the share of boundaries within 1 s.

## Baselines
- Ball rule: P(play) = 1 where the ball is detected in at least half of the surrounding second, else 0.
- VideoMAE game-state checkpoint (published with the dataset; trained on it, so it is evaluated as an upper
  reference, and on the test matches only if its training split is known to exclude them).
