# Court keypoint model: results

All numbers come from scripts run on the labelled splits; "end-to-end" means a homography fitted from the
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
| v3 YOLO26s-pose 1280 px, 400 ep | k6y7r + VNL clips 1-3 (completed) | pending | pending (clips 4-5 only) | |

The v1 row is per-point error (before the end-to-end script existed); v2 per-point for comparison:
k6y7r 0.53 m median, VNL 2.42 m median.
