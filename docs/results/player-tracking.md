# Player tracking

Change: `openspec/changes/add-player-tracking`. Code: `vball.players`; evaluation:
`scripts/eval_player_tracking.py` (TrackEval, MOTChallenge format), `scripts/analyze_tracking_errors.py`.

## Data
SportsMOT volleyball validation sequences (CC BY-NC 4.0): 15 sequences, 5,355 frames at 25 fps, 59,633
boxes, 12 labelled players per sequence. Only players on court are labelled; referees, bench and crowd are
not. Sanity check: the ground truth fed back as a tracker scores 1.0 on every metric
(`--gt-as-tracker`).

## Baseline grid (2026-10-08)
Pretrained YOLO26 (COCO person), Ultralytics trackers, detection at 10 fps with linear interpolation in
between, all 15 sequences; TrackEval's combined scores. Time: CPU (Apple M1 Pro) per detected frame.

| Detector | Input | Tracker | HOTA | IDF1 | MOTA | Recall | Precision | ID switches | ms / frame |
|---|---|---|---|---|---|---|---|---|---|
| YOLO26n | 960 | BoT-SORT | 0.378 | 0.388 | 0.117 | 0.835 | 0.542 | 707 | 59 |
| YOLO26n | 960 | ByteTrack | 0.275 | 0.293 | −0.007 | 0.743 | 0.506 | 1390 | 54 |
| YOLO26n | 1280 | BoT-SORT | 0.378 | 0.373 | −0.116 | 0.858 | 0.471 | 677 | 86 |
| YOLO26n | 1280 | ByteTrack | 0.269 | 0.282 | −0.145 | 0.765 | 0.463 | 1348 | 82 |
| **YOLO26s** | **960** | **BoT-SORT** | **0.456** | **0.470** | **0.240** | **0.889** | **0.581** | **515** | **95** |
| YOLO26s | 960 | ByteTrack | 0.318 | 0.340 | 0.130 | 0.803 | 0.552 | 1278 | 91 |
| YOLO26s | 1280 | BoT-SORT | 0.432 | 0.433 | −0.041 | 0.895 | 0.491 | 504 | 146 |
| YOLO26s | 1280 | ByteTrack | 0.314 | 0.332 | −0.070 | 0.812 | 0.485 | 1238 | 140 |

Raw outputs: `outputs/player_tracking/<config>.txt` (per-sequence rows included).

**Reading.** BoT-SORT halves the ID switches of ByteTrack in every setting. The small model beats the nano
model; 1280 px input adds recall but more false boxes and costs 50% more time. Best: YOLO26s, 960 px,
BoT-SORT. It misses the PRD targets (IDF1 ≥ 0.70, recall ≥ 0.95).

## Where the error comes from
Precision is about 0.5 in every setting: a COCO person detector also boxes referees, line judges, bench
and crowd, which SportsMOT does not label. For the best configuration, the tracker made 1,065 tracks for
180 labelled players; 577 of them (39% of the boxes) never or rarely overlap a labelled player.

Upper bound for on-court filtering (`analyze_tracking_errors.py`): keep only tracks that match a labelled
player in at least half their frames. This uses the labels, so it is the best any on-court filter could do,
not a result.

| | HOTA | IDF1 | MOTA | Recall | Precision | ID switches |
|---|---|---|---|---|---|---|
| YOLO26s 960 BoT-SORT | 0.456 | 0.470 | 0.240 | 0.889 | 0.581 | 515 |
| same, ideal on-court filter (upper bound) | 0.565 | 0.613 | 0.824 | 0.884 | 0.944 | 483 |

**Consequence.** On-court filtering (task 2.2, needs the court mapping) is worth building: it removes most
false boxes. It cannot reach the IDF1 target alone: the 488 player tracks average 2.7 tracks per player,
so identities break at occlusions and crossings, and recall stays at 0.88.

## Detection rate (2026-10-08)
YOLO26s, 960 px, BoT-SORT; detection every Nth frame of the 25 fps sequences, linear interpolation between.
Time for a 2-hour match = 7,200 s × detection rate × ms per detected frame (M1 Pro CPU, this stage only).

| Detection rate | HOTA | IDF1 | Recall | Precision | ID switches | Upper bound IDF1 (ideal filter) | 2-hour match |
|---|---|---|---|---|---|---|---|
| 25 fps (every frame) | 0.496 | 0.500 | 0.889 | 0.610 | 545 | 0.645 | ~4.8 h |
| **10 fps** | **0.456** | **0.470** | **0.889** | **0.581** | **515** | **0.613** | **~1.9 h** |
| 5 fps | 0.235 | 0.242 | 0.730 | 0.425 | 1304 | 0.352 | ~0.95 h |

**Decision: 10 fps by default.** It keeps most of the every-frame quality (IDF1 0.470 vs 0.500) in 40% of
the time. At 5 fps the gaps between detections are too long and tracks break (ID switches more than
double). The PRD's time budget (a 2-hour match in ≤ 1 h for this stage) is **not met**: 1.9 h. Options:
YOLO26n at 10 fps (59 ms per frame, ~1.2 h, IDF1 0.388), a GPU, or running the stage only inside rallies.
