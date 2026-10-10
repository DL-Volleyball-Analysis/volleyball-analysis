# Court keypoint model: results

All numbers come from `scripts/eval_court_keypoints.py` on the labelled splits; "end-to-end" means a homography fitted from the
model's floor points with confidence ≥ 0.5 (RANSAC), with the labelled image points mapped through it and
compared with their true court positions in metres. Ultralytics' pose mAP is not used for decisions: on
`test_vnl` (v1, v2) it is 0 because the labelled boxes cover only the front zone.

## Label completion (2026-10-08, on k6y7r labels, 640 × 640 images)
| Completion | Images | Median | p90 |
|---|---|---|---|
| Other floor points from the 4 front-zone corners | 270 | 2.1 px | 10.3 px |
| Net points from floor points via calibration (not used as labels) | 363 (33 collinear, 63 no focal) | 5.3 px | 29.4 px |

## Models
| Model | Data | k6y7r test, end-to-end | `test_vnl`, end-to-end | Notes |
|---|---|---|---|---|
| v1 YOLO26n-pose 960 px, 150 ep | k6y7r | per-point median 1.54 m | per-point median 8.64 m | wrong flip_idx (sidelines swapped in mirrored samples) |
| v2 YOLO26n-pose 960 px, 300 ep | k6y7r | median 0.49 m, p90 3.37 m, ≤ 0.3 m 31%, no fit 9/39 | median 1.35 m, p90 1.77 m, no fit 334/862 (all 5 clips) | attack lines placed ~4.8 m from centre on VNL paint |
| v2 (same splits as v3) | k6y7r | median 0.49 m, p90 3.37 m, ≤ 0.3 m 31%, no fit 9/39 | median 1.43 m, p90 19.5 m, ≤ 0.3 m 0%, no fit 158/275 (clips 4-5) | |
| v3 YOLO26s-pose 1280 px, **interim: epoch 103 of 400** (`best.pt`) | k6y7r + VNL clips 1-3 (completed) | median 7.91 m, p90 19.1 m, ≤ 0.3 m 1%, no fit 3/39 | **median 0.17 m**, p90 0.31 m, ≤ 0.3 m **89%**, no fit 0/275 (clips 4-5, never trained on) | training stopped at epoch 103 (Colab GPU quota) |

The v1 row is per-point error (before the end-to-end script existed); v2 per-point for comparison:
k6y7r 0.53 m median, VNL 2.42 m median.

## v3 interim (2026-10-10, epoch 103 of 400)
On the held-out broadcast clips v3 is the first model to meet the 0.3 m target: median 0.17 m (clip four
0.16, clip five 0.21), 89% of points within 0.3 m, against 1.43 m for v2 on the same images. On the k6y7r
test images it is far worse than v2 (7.91 m): its points are not mirrored (renumbering them as mirrored makes
the pixel error larger, 147 → 206 px median) but misplaced, often bunched to one side as on the broadcast
court. The completed broadcast labels were checked on images and follow the k6y7r numbering.

Reading: the 294 broadcast frames come from three clips, every second frame, so they are near-duplicates that
the model fits quickly; the 347 k6y7r images span many courts and views and lag behind (validation pose
mAP50 about 0.1 at epoch 103, against about 0.3 for v1 at the same epoch). Training continues; `best.pt` is
selected on the k6y7r validation split. If k6y7r stays worse than v2 at the end, the next run (v3b) samples
broadcast frames sparsely (every 6th frame) so they do not dominate: amateur footage, the product's target,
looks more like k6y7r than like broadcast.

## v3b (2026-10-10): one box convention
Checking the v3 labels showed two box conventions: the k6y7r annotators' boxes are median 2.8x (p90 24x) the
extent of the floor keypoints, while the boxes computed for the completed broadcast labels are 1.1x. A pose
model regresses keypoints relative to its box, so the mix plausibly explains why v3 fitted the broadcast clips
and not k6y7r. v3b recomputes every box as the keypoints' bounding box plus a 1% margin (checked: ratio 1.00
for both sources, keypoints unchanged) and changes nothing else, fine-tuning from v3's epoch-103 weights.

## v3b result (2026-10-11): best on broadcast, still wrong on gym images
Colab stopped at epoch 184 of 250 (validation pose loss 5.07 -> 5.00 over the last 30 epochs). End to end,
`scripts/eval_court_keypoints.py --dataset court_keypoints_v3b`, median court-position error:

| Model | k6y7r test (gym, 39 images) | VNL clips four-five (broadcast, 275) | broadcast within 0.3 m |
|---|---|---|---|
| v2 | **0.49 m** (9 no fit) | 1.43 m (158 no fit) | 0% |
| v3, epoch 103 | 7.91 m | 0.17 m | 89% |
| v3b best | 7.28 m | **0.10 m** (0 no fit) | **96%** |
| v3b epoch 180 | 6.35 m | 0.09 m | 94% |

The box convention was not the cause of the gym failure. A mirrored numbering is not either: relabelling v3b's
predictions left-right, far-near or by 180 degrees helps no consistent share of the images (best permutation per
image: as is 17, rot180 8, far-near 7, left-right 5), while v2 is right as is on 28 of 31. v3b's predictions on
gym images are simply poor: training is dominated by near-duplicate frames of three broadcast clips and starts
from v3. Options: pick the model per shot with the floor-net consistency check (no labels needed), or retrain with
fewer VNL frames from pretrained weights.

## Court stage on the evaluation clips (2026-10-10, model v2)
`vball.court_registration` in the web app's court stage (5 samples per second per shot, model v2 installed
as `models/court_kpt.pt`), on the five 1080p evaluation clips:

| Clip | View | Stage time / video | Status (self-reported) | By eye (`outputs/court_v2_overlays.jpg`) |
|---|---|---|---|---|
| broadcast_back_rally | behind the end line | 0.60x (includes model load) | ok, error 0.0038 | wrong |
| broadcast_back_view | behind the end line | 0.32x | ok, 0.0027 | wrong: full court squeezed into the near half |
| broadcast_side_high_men | high on the side | 0.34x | ok, 0.0009 | right |
| broadcast_side_high_women | high on the side | 0.33x | ok, 0.0010 | right |
| broadcast_side_rally | behind the end line | 0.36x | ok, 0.0027 | wrong: full court squeezed into the near half |

Overall 0.38x the video duration (budget 0.5x). **2 of 5 correct by eye** (the geometric detector: 1 of 5);
the target is 4 of 5. All three views from behind an end line fail the same way, mapping the 18 m court onto
the near 9 m half, as the geometric detector once did.

The self-reported status said ok for all five: the model's points agree with each other, they are just all
in the wrong place, so a small reprojection error does not show it (the calibration focal gate addresses the
same kind of problem in 3D). A check that would catch it: from behind an end line the net stands on the
centre line, so the predicted net points (10-13) should sit above the projected centre line; a shot where they
do not should be needs_review. To be added, and the overlays redone with v3b.

### Floor-net consistency check (2026-10-10)
Per sample, a camera calibrated on the floor keypoints alone projects the net; the distance to the detected
net points (median per shot) is the shot's consistency. With v2 on the evaluation clips:

| Clip | By eye | Net distance, median of 8 frames | Status now |
|---|---|---|---|
| broadcast_back_view | wrong | 58 px | needs_review |
| broadcast_side_rally | wrong | 86 px | needs_review |
| broadcast_back_rally | wrong | 116 px | needs_review |
| broadcast_side_high_men | right | 14 px | ok |
| broadcast_side_high_women | right | 9 px | ok |

Threshold 1.5% of the width (~29 px at 1080p): the status now agrees with the eye on 5 of 5, and only ok shots
feed the players, trajectory and events stages. A first version calibrated on all 14 points and missed it: the
robust loss treated the four net points as outliers. Synthetic checks: a clean squeeze of the floor into the
near half from behind an end line gives 130 px, a correct view ~1 px.

### Model per shot on the evaluation clips (2026-10-11)
The court stage now runs v2 (`court_kpt.pt`, "gym") and v3b (`court_kpt_broadcast.pt`, "broadcast") and keeps the
better per shot (status, then floor-net consistency, then fit error). Per model, one shot per clip:

| Clip | v2 (gym) | v3b (broadcast) | Used |
|---|---|---|---|
| side_high_men | ok, consistency 15 px, error 0.0009 | ok, 13 px, 0.0015 | broadcast |
| side_high_women | ok, 9 px, 0.0010 | ok, 13 px, 0.0017 | gym |
| back_rally | needs review, 127 px, 0.0038 | needs review, 243 px, 0.034 | gym (needs review) |
| back_view | needs review, 72 px, 0.0027 | needs review, 2 of 71 samples fit, 0.036 | gym (needs review) |
| side_rally | needs review, 81 px, 0.0027 | needs review, 11 of 43 samples fit, 0.035 | gym (needs review) |

Both models are right on the two high side views. The back views and the low Tokyo 2020 side view are beyond
both: v3b is confident on every point there but its points are geometrically inconsistent (fit error 10x v2's),
having been trained on high side broadcast views only. The pick never chose a wrong court, and the doubtful shots
stay needs review. Fixing them needs training images from those angles.
