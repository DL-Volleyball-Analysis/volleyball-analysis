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

| Clip | View | Stage time / video | Status (self-reported) | By eye (`outputs/court/v2_overlays.jpg`) |
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

## Net points and inference time (2026-10-11)
`scripts/eval_court_keypoints.py --dataset court_keypoints_v3b` now also reports the pixel error of the four net
points (10-13) where they are labelled (k6y7r test, 1080p-scale images) and the model's time per image on the
M1 Pro CPU (model call only, median).

| Model | k6y7r test (metres) | Net points, k6y7r test | `test_vnl` (metres) | Time per image |
|---|---|---|---|---|
| v2, YOLO26n-pose 960 px (`court_kpt.pt`, "gym") | median 0.49 m, p90 3.37 m, no fit 9/39 | median 8.7 px, p90 136 px | median 1.43 m, no fit 158/275 | 93 ms |
| v3b, YOLO26s-pose 1280 px (`court_kpt_broadcast.pt`, "broadcast") | median 7.28 m, p90 18.8 m, no fit 2/39 | median 21.2 px, p90 394 px | **median 0.10 m**, p90 0.19 m, 96% ≤ 0.3 m | 285 ms |

The court stage samples a few frames per shot, so even v3b's 285 ms adds about a second per shot. Net-point
errors follow the floor errors: v2 places the net well on gym images, v3b does not.

## Why most videos have no usable court (2026-10-12)
Of nine analysed videos, three have a usable court shot. Overlays of the fitted floor on the first sample:

- Broadcast back / side rally views: the floor fit is correct (projected lines on the sidelines and centre line), but
  the net check fails (net error 0.04-0.07 of the image width, threshold 0.015): the model puts the net points at the
  ends of the net, about 1 m outside the sidelines, where the check expects them above the sidelines.
- 4K low end-line gym view (Canada vs Italy): the floor fit follows lines of other sports; the net check correctly
  rejects it.
- Measuring the net points' distance to the projected net line instead of to the points passes the correct back views
  (0.007-0.021) but also the wrong gym fit (0.014): the net alone cannot tell the two apart. Change
  `verify-court-by-lines` proposes line evidence from the image instead.

> The 4K moving-camera clips referred to above (Canada vs Italy, Choforo55 gym, Hawaii vs UCI, Long Beach vs UCLA) were removed on 2026-10-12 at the owner's request; testing moved to fixed end-line camera clips (data/videos/fixed).

## Fixed end-line cameras: court from painted lines (2026-10-12)
Six 3-minute clips from fixed cameras high behind an end line (VolleyballWatchdog, NCAA men's volleyball, five
arenas; data/videos/fixed, kept local). Both keypoint models fail on all six: the broadcast model finds no court, the
gym model squeezes the court into the near half (the far end line on the net), and the net check passes some of these
(0.007 on Hawaii vs Penn State).

`vball.court_lines` (change verify-court-by-lines) fits the court model to the painted lines of each clip's background
plate (median of 60 frames: players gone). Line evidence of the chosen fit, checked by eye on overlays:

| Clip | Floor | Lines | Good court lines (of 7) | Line samples supported | Search |
|---|---|---|---|---|---|
| gcu_ucla | multi-sport, volleyball lines black, basketball lines white | dark | 7 | 0.79 | 2 s |
| hawaii_irvine | volleyball only | white | 7 | 0.94 | 0.3 s |
| hawaii_pennstate | volleyball only | white | 7 | 0.97 | 4 s |
| quincy_ballstate | multi-sport, thin white lines, busy stands | white | 5 | 0.74 | 33 s |
| ucla_concordia | multi-sport, basketball lines | white | 6 | 0.76 | 9 s |
| usc_pepperdine | volleyball only, large logo | white | 6 | 0.85 | 9 s |

All six looked correct by eye (court lines on the painted lines). Corrected 2026-10-13 by labelled floor points (section
below): five are right to a few centimetres, Quincy is wrong by about 1 m. What it took, each step found on these clips:
- Line pixels by the brighter-than-both-sides test (Farin et al.) instead of a white top-hat: the top-hat kept wood
  grain and crowd texture, and the search then preferred courts squashed onto a stripe.
- A per-line support term in the score, and rejecting fans and slivers (interior angle under 25 deg).
- Dark lines (GCU paints volleyball lines black).
- A floor test: perspective (some court direction vanishes within 20 image widths), a near-horizontal horizon with the
  court below it. Without it a scoreboard panel on the Quincy wall won. A focal-length test does not work: a symmetric
  end-line view leaves the focal length undetermined.

## Line fit on light floors: a whiteness channel, tried and not adopted (2026-10-13)
Two full Watchdog matches have no usable court (Pepperdine: thin white lines on a light grey floor with many light
reflections; McKendree: white lines on light orange wood). Their white lines differ from the floor more in saturation
than in brightness, so the line test was run on V - S (bright and unsaturated) instead of grey, as a third mask next to
bright and dark lines, the best-scoring fit winning:

| Plate | Bright: support / good lines | Dark | Whiteness | Picked court |
|---|---|---|---|---|
| fixed_gcu_ucla | 0.27 / 3 | **0.82 / 7** | 0.39 / 4 | same as before (dark lines) |
| fixed_hawaii_irvine | 0.94 / 7 | none | **1.00 / 7** | same court, more support |
| fixed_hawaii_pennstate | 0.98 / 7 | 0.55 / 3 | **1.00 / 7** | same |
| fixed_quincy_ballstate | 0.74 / 5 | 0.51 / 5 | **0.72 / 6** | same |
| fixed_ucla_concordia | 0.76 / 6 | 0.73 / 3 | **0.78 / 6** | same |
| fixed_usc_pepperdine | 0.86 / 6 | 0.26 / 1 | **0.99 / 7** | same |
| Pepperdine (full match) | **0.57 / 6** | 0.55 / 4 | 0.52 / 5 | still wrong (pulled by reflections) |
| McKendree (full match) | 0.43 / 4 | 0.41 / 4 | **0.65 / 6** | still wrong (squeezed into the far half; the near end line is likely hidden under the banner at the bottom edge) |

Whiteness raises the support of correct fits but does not fix the two failures, which stay below the 0.70 gate and are
still flagged needs_review. Not adopted: it would change every court result (stage version bump) without the gain it
was meant for. Next ideas: mask specular highlights (bright blobs that move between frames of the plate's input) and
allow fits whose near end line is outside the image.

## Fixed end-line cameras: court error in metres from labelled floor points (2026-10-13)
Verify-court-by-lines task 3.1. On each clip's background plate the owner clicked six floor points (near end line and
near attack line where they meet the sidelines, and the centre line under the net at both sidelines;
`scripts/eval_fixed_court.py`, labels in `outputs/court/fixed_labels/labels.json`). Each click is mapped to the court
with the app's court for that shot and compared with the point's true position (under the court's symmetry).

| Clip | Median error | Max error | Line support / good lines | Focal length from the net |
|---|---|---|---|---|
| fixed_hawaii_pennstate | 0.018 m | 0.027 m | 0.98 / 7 | 5424 px |
| fixed_ucla_concordia | 0.024 m | 0.063 m | 0.75 / 6 | 4340 px |
| fixed_hawaii_irvine | 0.032 m | 0.038 m | 0.94 / 7 | 4969 px |
| fixed_usc_pepperdine | 0.050 m | 0.100 m | 0.85 / 6 | 3810 px |
| fixed_gcu_ucla | 0.058 m | 0.469 m | 0.79 / 7 (dark lines) | not found |
| **fixed_quincy_ballstate** | **1.058 m** | **2.488 m** | 0.78 / 5 | **801 px** |

All 36 points: median 0.041 m, 86% within 0.3 m. The five right courts: median 0.032 m, 97% within 0.3 m.

**Quincy is wrong, which the by-eye check had missed.** Its near attack line is right (0.05 and 0.14 m), so the overlay
looks plausible, but the court is stretched in depth: the centre line is drawn about 1 m in front of the net posts and
the near end line about 2.4 m beyond the real one, outside the image. The earlier statement "right on all six clips by
eye" is corrected to five of six. Two signs stand out on this clip only: the fewest supported lines (5 of 7) and a focal
length from the net tape about five times shorter than on the other clips, the stretched floor forcing a wide-angle
camera. Both are candidate checks for a doubtful line fit; they were noticed on this test set, so they need other arenas
before they become a rule.

## Court set v4: our labels, one numbering, baseline (2026-10-16)
Change add-labelling-loop. The owner labelled 59 images in CVAT (14 points each): 43 amateur recordings (one plate per
recording, YouTube and the owner's own), 10 broadcast frames and 6 Watchdog end-line plates. Each label is checked
against a court homography (`scripts/cvat_labels.py check`); all 517 placed floor points: median 0.07 m from the fit
(p90 0.65 m). Eight labels with errors above 1.5 m were re-checked and corrected by the owner. The remaining misfits lie
along the far sideline of low views (12-40 px, mostly 0.3-0.6 m), where cross lines meet it at a grazing angle; a
lens-distortion term does not explain them. They are kept as placed. Points are straightened onto their sideline or net
post (`cvat.straighten`, median move 0.6 px).

**Numbering.** A court looks the same turned by 180 degrees, so two numberings fit every view. End-line and corner views
were mixed: in k6y7r 20 unmirrored images use one, 40 the other, its own mirrored images both; ultralytics' mirror with
a fixed flip_idx turns one into the other; our end-line labels use the second. Three labels were mirror-numbered (two
k6y7r, one ours). v4 renumbers every label by one rule (`court_keypoints.canonical_numbering`, no label near its
boundary) and makes the mirrored training copies itself, renumbered, so training runs with fliplr=0. The evaluation
counts the better of the two numberings per image (never a mirror), which changes v3b on k6y7r test from 7.28 to 5.96 m.

**Splits** (by recording): train 27 amateur recordings (repeated 3 times) and the 10 broadcast frames; valid 5 amateur;
`test_amateur` the owner's 5 recordings (4 sessions) and 6 amateur videos; `test_watchdog` the 6 Watchdog plates.

Baseline before fine-tuning (`scripts/eval_court_keypoints.py --dataset court_keypoints_v4`, median error in court metres,
share within 0.3 m, images without a fit):

| Model | k6y7r test | VNL clips 4-5 | test_amateur (11) | test_watchdog (6) |
|---|---|---|---|---|
| v2 (gym) | 0.49 m (31%), 9 no fit | 1.43 m (0%), 158 no fit | 4.21 m (2%), 1 no fit | 1.64 m (3%) |
| v3b (broadcast) | 5.96 m (5%), 2 no fit | 0.10 m (96%) | 8.51 m (1%), 2 no fit | 7.75 m (0%), 3 no fit |

Neither model registers amateur recordings: the best per image is 0.8-1.0 m (two recordings, v2), most are 3-11 m off.
Fine-tuning v3b on v4 (`notebooks/train_court_keypoints.ipynb`, 150 epochs at 1280 px) is the next step.
