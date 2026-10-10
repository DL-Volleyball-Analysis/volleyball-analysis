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

## Stage time in the web app (2026-10-08)
`scripts/time_player_stage.py`: the players stage's own configuration (YOLO26s, 960 px, BoT-SORT, 10 fps)
on the 5 evaluation clips, decoding included (M1 Pro CPU):

| Clip | Frames | fps | Time | × real time |
|---|---|---|---|---|
| broadcast_back_rally | 226 | 30 | 9.8 s | 1.30 |
| broadcast_back_view | 420 | 30 | 15.4 s | 1.10 |
| broadcast_side_high_men | 153 | 30 | 5.5 s | 1.08 |
| broadcast_side_high_women | 178 | 30 | 6.5 s | 1.09 |
| broadcast_side_rally | 421 | 50 | 9.7 s | 1.15 |

Overall 1.14 × real time: a 2-hour match takes about **2.3 h** for this stage, more than the 1.9 h
estimated from detection time alone (decoding every frame adds the rest). PRD budget (≤ 1 h): not met.

## Interpolation across long gaps (2026-10-10)
Rendering analysed videos showed empty boxes: tracks lost by the tracker and picked up again much later were
interpolated straight through the frames where the person was not seen. `track_frames` now bridges at most
three sampling intervals (`MAX_GAP_SAMPLES`). Rerun of the best setting (YOLO26s, 960 px, BoT-SORT, 10 fps):

| | HOTA | IDF1 | MOTA | Recall | Precision | ID switches |
|---|---|---|---|---|---|---|
| before (any gap bridged) | 0.456 | 0.470 | 0.240 | 0.889 | 0.581 | 515 |
| **after (≤ 3 intervals)** | **0.467** | **0.484** | **0.316** | 0.875 | **0.614** | 522 |
| after, ideal on-court filter (upper bound) | 0.572 | 0.622 | 0.850 | 0.874 | 0.982 | 508 |

The ghost boxes were counted as false positives: precision +3.3 points, MOTA +0.08, at a small recall cost
(some long gaps had been bridged correctly). The PRD targets are still missed. Raw output:
`outputs/player_tracking/yolo26s_960_botsort_10fps_gap3*.txt`.

## Role check by appearance (2026-10-11, change filter-on-court-players)
`scripts/eval_roles.py` (output in `outputs/roles_eval.txt`): on the saved YOLO26s 960 BoT-SORT tracks of the 15
SportsMOT volleyball val sequences, a predicted track is a non-player when it matches no labelled player (IoU >=
0.5 on at least half its boxes). No court mapping here, so this is colour alone (no libero override).

| Team centres fitted on | non-player boxes marked other | player boxes marked other | box precision |
|---|---|---|---|
| all tracks | 3.1% | 0.1% | 0.613 -> 0.620 |
| tracks seen in >= 30% of frames (installed) | **33.1%** | **1.1%** | **0.613 -> 0.700** |

Non-player tracks outnumber the players' (577 vs 488): spectators, bench and staff in many colours pull two-team
clustering apart. Players stay in view (median 21% of frames per track against 10%), so only long tracks define the
teams. The thresholds were chosen on these sequences, so the gain is optimistic until confirmed on the SportsMOT
training sequences (downloaded with task 1.2). A precision of 0.700 is still far from the 0.95 of an ideal filter:
the player-only detector (task 1) is the main remedy, this check the fallback without a court.
