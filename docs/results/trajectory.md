# 3D ball trajectory

Change: `openspec/changes/add-ball-trajectory-3d`. Code: `vball.calibration`, `vball.trajectory`.

## Synthetic rallies (2026-10-08)
`scripts/eval_trajectory_synthetic.py --seeds 20 --noise 2`: a serve → receive → set → attack rally
rendered through a known camera (behind the near sideline, 14 m back, 7.5 m up, f = 1600 px, 1080p,
50 fps) with 2 px Gaussian detection noise; true camera and true flight boundaries, so the numbers
isolate the ballistic fit.

| Flight | Duration | Median 3D error | p90 | Reported depth sd (median) | Worst error / sd | Low quality |
|---|---|---|---|---|---|---|
| serve | 1.32 s | 0.047 m | 0.116 m | 0.19 m | 0.93 | 0/20 |
| receive | 1.12 s | 0.113 m | 0.273 m | 0.29 m | 1.46 | 0/20 |
| set | 0.92 s | 0.171 m | 0.307 m | 0.41 m | 1.35 | 4/20 |
| attack | 0.46 s | 0.950 m | 1.597 m | 2.46 m | 1.14 | 20/20 |

Segmentation found every touch within 2 frames in 20/20 rallies.

**Reading.** One camera recovers depth only from the apparent curvature that gravity gives the path.
Long flights across the view meet the spec's 0.10 m (serve: 0.047 m); shorter flights and flights
toward the camera do not. The reported depth uncertainty is honest: the mid-flight error never exceeded
1.5 reported standard deviations, so "ok" flights can be trusted and the others are flagged.

**Consequence for landing calls.** A spike lasts under half a second and is always flagged low quality
here, yet it is the flight whose landing decides most points. A floor constraint (the flight ends where
the last detection's ray meets the floor) would fix the end point without curvature; it needs the events
stage to say which flights end on the floor and is not in the current change. Proposed as a follow-up.

**Thresholds** (`FlightConfig`): touch detection uses an 8-frame window and an 8 px/frame velocity jump
(interior jumps from 2 px noise stay below ~5 px/frame, touches are above ~13); touches closer than about
0.3 s at 50 fps are not separated. Low quality: median residual > 4 px or depth sd > 0.5 m.

## Camera calibration on labelled images (2026-10-08)
`scripts/eval_calibration.py`: k6y7r test split (49 images, 640 px), calibrated from the labelled keypoints
and from court model v2's keypoints with confidence ≥ 0.5. Gates: median reprojection error ≤ 0.5% of the
image width, focal length relative sd ≤ 5%.

| Keypoints from | Usable | Median reprojection error | p90 | Camera height (median) | Unusable: < 4 floor points / focal undetermined / error above gate |
|---|---|---|---|---|---|
| labels | 30 / 49 | 1.03 px (0.16% of width) | 2.40 px | 4.9 m | 10 / 7 / 2 |
| model v2 | 4 / 49 | 2.19 px (0.34%) | 2.30 px | 7.0 m | 10 / 21 / 14 |

**Reading.** With correct keypoints, calibration works on most views with enough of the court (net height
picked: 2.43 m in 22, 2.24 m in 8). With v2's keypoints it rarely does: too few confident points, or
points inconsistent with any camera, which matches v2's systematic attack-line error
([court-keypoints.md](court-keypoints.md)). 3D trajectories on real footage therefore depend on court
model v3.

**Focal gate.** A view that shows only one sideline and the net, roughly head-on, puts every visible
point in one vertical plane; zoom and distance then trade off and many cameras fit to sub-pixel error
(synthetic: the fit picked f = 2001 px for a true 1600 px). The second gate rejects these instead of
returning a confident wrong camera (focal sd 37-78% in that case, 0.4% with the whole court).

## Real footage
Not measured yet (task 8.1): net-crossing heights on the evaluation clips, once a court model gives
usable calibrations on them.

## Detection errors on the evaluation clips (2026-10-11)
For realistic synthetic tests (change `constrain-3d-flights`). Missed = frames without a VballNet V4c detection;
isolated outliers = detections more than 30 px from the line joining their neighbours (neighbours at most 6 frames
apart), a conservative lower bound on false detections since a ball cannot jump that far between frames.

| Clip | Frames | Missed | Isolated outliers |
|---|---|---|---|
| back_rally | 226 | 26.5% | 14.5% |
| back_view | 420 | 26.2% | 6.5% |
| side_high_men | 153 | 71.9% | 51.7% |
| side_high_women | 178 | 33.1% | 18.9% |
| side_rally | 421 | 23.3% | 0.3% |
| frame-weighted | | 31.3% | 12.5% |

The synthetic ablation uses 30% missed (in bursts of about 4 frames) and 12% false detections. On the wide
men's clip the ball is too small: 72% missed and half the rest wrong.

## Ablation on realistic detection errors (2026-10-11)
`scripts/eval_trajectory_synthetic.py --ablation`: the serve -> receive -> set -> attack rally (1080p, 50 fps),
detections corrupted as measured above (30% missed in bursts, 12% false points, 2 px noise), true flight
boundaries, a player about 0.3 m from each touch's ground point. Median 3D error per flight:

| Fit | serve | receive | set | attack (0.45 s) |
|---|---|---|---|---|
| no constraints | 0.08 m | 0.20 m | 0.40 m | 0.87 m |
| + bounds | 0.08 m | 0.20 m | 0.40 m | 0.87 m |
| + robust refit | 0.09 m | 0.17 m | 0.29 m | 0.76 m |
| + player anchors | **0.05 m** | **0.11 m** | **0.12 m** | **0.31 m** |

- Player anchors are the large gain: the attack's error drops by 59% against the robust fit (64% against no
  constraints), the set's by 59%. All 140 touches with a player were anchored; the robust refit dropped 335
  detections.
- Bounds change nothing here, as expected: with true boundaries the fit never prefers a ball at the camera.
  They exist for real tracks, where that solution appeared (test: a path in front of the camera is kept in the
  hall and marked low quality instead of drawn at the lens).
- Synthetic players stand at the touch; on real footage the nearest player to the ray may not be the one who
  touched the ball, which the real-clip report has to show.

## Real clips with the constrained fit (2026-10-11)
Trajectory stage version 3 (robust refit, bounds, player anchors from the players placed on court). Only the two
high side views have a usable court; the men's calibration is the v3b one chosen per shot.

| Clip | Segmented | Kept (all low quality) | Rejected as impossible | Kept and anchored |
|---|---|---|---|---|
| side_high_women | 9 | 5 (was 0) | 4 | 5 |
| side_high_men | 3 | 1 (was 0) | 2 | 1 |

- The kept flights now lie on court: starts at 2-3 m height inside the court, speeds 3-18 m/s, no fit at the camera.
- Two women's flights fit to 2.6-2.8 px with both ends anchored; they stay low quality only on depth (sd 0.68 and
  1.30 m against 0.5 m). The others have residuals of 10-120 px: their segments mix flights or carry many false
  detections, which no fit can explain.
- The bottleneck has moved from the fit to the 2D ball track and its segmentation (change `measure-ball-2d`): on
  the men's clip 72% of frames have no detection.
