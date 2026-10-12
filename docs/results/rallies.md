# Rally detection

Change add-rally-detection. `scripts/eval_rallies.py` on the game-state dataset of masouduut94/volleyball_analytics:
8 full broadcast matches with CVAT tags serving-start, serving-end and in-game-end for every rally (680 rallies; a
labelled rally runs from serving-start to in-game-end). Test matches 6 and 9 (41 + 179 = 220 rallies, one from each
recording batch); the other six matches train the classifier and choose the segmentation thresholds by
leave-one-match-out (out-of-fold predictions). Cues per sample at 5 Hz (`scripts/extract_rally_cues.py`, Kaggle
`notebooks/extract_rally_cues.ipynb`): court keypoint confidence and whether a plausible court is fitted, number and
motion of player boxes, share of frames with a ball detection and ball speed. A detected rally matches a labelled one at
temporal IoU >= 0.5 (one to one).

## Results on the test matches (2026-10-11)
| Method | Precision | Recall | F1 | Median start error | Median end error | Boundaries within 1 s | Sample accuracy |
|---|---|---|---|---|---|---|---|
| Ball rule (ball detected in half of the surrounding second) | 0.467 | 0.386 | 0.423 | 1.23 s | 0.70 s | 52% | 0.728 |
| **Classifier on the system's cues** | **0.758** | **0.727** | **0.742** | **0.52 s** | **0.60 s** | **66%** | **0.859** |

Per match (classifier): match 6 P 0.735 R 0.878 F1 0.800 (36 of 41); match 9 P 0.765 R 0.693 F1 0.727 (124 of 179).
Chosen segmentation: smoothing 1 s, open and close at 0.5, rallies of at least 3 s, gaps under 0.5 s merged.

- **The court, the players and the ball together beat the ball alone** (F1 0.742 against 0.423). Between rallies the
  broadcast shows close-ups and replays: no court, few players; the ball alone is often missed during play (see
  docs/results/ball-tracking.md) and seen in hands between rallies.
- **Model selection matters.** A first version chose its thresholds on two validation matches (3 and 10) whose rallies
  are long (median 450-490 frames); it picked a 4 s minimum and lost the short rallies of the condensed match 9 (test
  F1 0.634, recall 0.550). Leave-one-match-out over six matches fixed it; the test matches were not used in either.
- Not yet compared: the published VideoMAE game-state checkpoint (trained on this dataset, so only a reference if its
  split is known). Not yet in the pipeline: the rallies stage still shows labelled demo rallies (task 3.1).

## In the pipeline, and where it does not apply (2026-10-12)
Rallies stage version 1 runs the model above (retrained on all eight labelled matches; `models/rally_cues_hgb.joblib`)
on the cues of `vball.rally_cues`, the same code that produced the training data. Detected rallies replace demo
rallies; a user's winner correction moves to the detected rally that overlaps it on a rerun; actions outside detected
rallies (warm-up, time-outs, replays) are left out of the actions API.

On footage unlike the training broadcasts it does not transfer. On a 4K low end-line view (Canada vs Italy) and a 4K
amateur-gym view (open gym, corner tripod) it found no rally at all: it learned play as "the court in view and the
player-only detector seeing both teams", and there the court model rarely finds the court and the player-only detector
sees 3-4 people. The stage now reports such videos as unavailable with the reason (court found in under 20% of the
samples, or a median under 6 people) instead of claiming there was no rally. On a 6 s broadcast clip that starts and
ends mid-rally it also found none (probabilities 0.1-0.6): the model sees rallies whole, with the time before and after.

Next: cues that do not depend on the view (ball motion, motion of the people on the floor relative to the video's own
range, cues normalised per video) and rally labels on gym footage to measure them.

> The 4K moving-camera clips referred to above (Canada vs Italy, Choforo55 gym, Hawaii vs UCI, Long Beach vs UCLA) were removed on 2026-10-12 at the owner's request; testing moved to fixed end-line camera clips (data/videos/fixed).
