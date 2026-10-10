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
