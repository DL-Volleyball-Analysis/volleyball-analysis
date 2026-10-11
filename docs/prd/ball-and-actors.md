# Ball detection and actor attribution, measured on labelled volleyball data

Version 1.0 · 2026-10-11 · Owner: YuJia Liang

## Why
- The 2D ball track is the bottleneck of the 3D stage: on the evaluation clips 31% (women) and 72% (men) of
  frames have no detection, and a look at the detections showed many false ones (floor dashes, scoreboard
  digits, spectators' heads). Until now ball tracking was judged with label-free proxies only.
- The action model fires on players who only look like they set or spike, so one track gets block then spike
  within a second. Nothing measured how often it names the wrong player.
- Both need labelled data before any change can be called an improvement.

## What
1. **Labelled evaluation of ball detection** on the Volleyball dataset (Ibrahim et al., CVPR 2016; 55 broadcast
   matches) with per-frame ball annotations (Perez et al., Pattern Recognition 2022), official test split.
2. **Candidate detectors and a tracker**: VballNet on the whole frame or on tiles at a higher resolution, the newer
   RAVEL-VB releases (1024 x 576 grey, 640 x 360 RGB) from the same upstream; a tracker that drops fixed objects
   (camera-compensated motion check), links candidates over time (Viterbi) and fills short gaps. An ablation
   decides what the pipeline uses.
3. **Actor attribution with the ball**: weight each player's action score by a prior on the distance from the
   ball to the player, and combine frames. Measured on the same dataset's per-player action labels (setting,
   digging, spiking, blocking), parameters chosen on the validation matches, reported on the test matches.

## Success
- Every number reported with its data, split and threshold; nothing tuned on the test split.
- The pipeline's ball method changes only if the labelled F1 improves; actor attribution enters the actions
  stage only if the test macro F1 improves over the action model alone.

## Out of scope
- Training a new ball detector (WASB-style HRNet) on this dataset: a later change if the ablation shows the
  detector, not the tracker, is the limit.
- Temporal action spotting models (T-DEED, E2E-Spot) and the VNL-STES data (13 GB, no scripted download).
