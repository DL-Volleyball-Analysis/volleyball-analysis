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
Net-crossing heights are measured in the section below (task 8.1). Previously: not measured, waiting until a court model gave
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

## Net-crossing check on the evaluation clips (2026-10-11, task 8.1)
Trajectory stage version 3 on the two clips with an ok court (the other three have no court, so no flights). Of
the 6 kept flights, 2 cross the net plane:

| Clip | Frames | Net-crossing height | Where (y) | Fit | Depth sd | Above the net top? |
|---|---|---|---|---|---|---|
| women | 13-24 | 0.74 m | -4.75 m (outside the court) | 119.9 px | 2.8 m | no: impossible, and flagged low quality |
| women | 115-129 | 2.41 m | 5.52 m | 29.7 px | 293 m | yes (net top 2.24 m), but the depth is unconstrained |

All 6 kept flights (100%) are low quality, as the stage reports. The one physically impossible crossing comes from a
flight that mixes two pieces of track (fit error 120 px); the check confirms that a low-quality flag is needed
before any landing or net call is made from these flights. The cause is upstream: the 2D ball track (see
`docs/results/ball-tracking.md`, labelled evaluation).

## Moving cameras (2026-10-12)
Change follow-camera-motion. Camera motion between frames is estimated by keyframe registration (`vball.camera_motion`)
and used for court smoothing, gap filling, court corrections and a camera per 3D flight.

Photometric check (mean absolute grey difference between a frame warped by the estimated motion and the frame 1 s / 3 s
later, 12 starting points per clip, top and bottom bands masked):

| Clip | Camera | 1 s: unwarped -> warped | 3 s: unwarped -> warped |
|---|---|---|---|
| broadcast_side_rally | still | 12.6 -> 12.6 | 14.2 -> 14.2 |
| hawaii_uci_4k60 (removed since) | broadcast, pans and cuts | 33.1 -> 18.5 | 42.5 -> 28.6 |
| canada_italy_4k60 (removed since) | handheld, pans | 23.1 -> 13.7 | 27.9 -> 15.9 |

A first version that chained frame-to-frame estimates drifted on the still camera (12.6 -> 19.7 at 1 s); registering
each frame to a keyframe fixed it.

3D flights rejected as physically impossible, before -> after (same court and ball results), on the two broadcast
clips whose camera pans: side_high_men 2 -> 1, side_high_women 4 -> 2. The Hawaii 4K clip that motivated the change (15 of
33 flights rejected with one calibration for a 64 s panning shot) was removed at the owner's request before it could
be rerun, so the larger before / after is not available.

## broadcast_back_view: court from the lines, 3D flights for the first time (2026-10-13)
This Tokyo 2020 view from behind the end line had an old user court correction that overrode the line fit; with it the
calibration failed (reprojection error 98.5 px against a 9.6 px gate) and the clip had no 3D flight. The correction was
lost in the 2026-10-13 database incident, and the rerun from the court stage lets line evidence decide: the court is
right by eye (far end line, far attack line, the centre line under the net posts, near attack line and near end line all
on the painted lines, attack-line dashes included). The shot calibrates and gives 16 flights, 2 left out as physically
impossible and 13 of the rest low quality: the 2D ball track remains the limit.

## 3D flights on every evaluation clip (trajectory stage 5, 2026-10-13)
Counts from the web app's analysis results (`flights.json`, `trajectory.json`). Kept flights passed the physical bounds;
rejected ones did not (e.g. faster than 40 m/s, a path below the floor); high quality = fit residual and depth
uncertainty both small. These are the system's own checks, not accuracy (there is no 3D ground truth).

| Clip | Length | Kept | Rejected | Rejected share | High quality |
|---|---|---|---|---|---|
| fixed_gcu_ucla | 3 min | 115 | 29 | 20% | 42 |
| fixed_hawaii_irvine | 3 min | 68 | 34 | 33% | 12 |
| fixed_hawaii_pennstate | 3 min | 102 | 102 | 50% | 15 |
| fixed_quincy_ballstate | 3 min | 187 | 53 | 22% | 43 |
| fixed_ucla_concordia | 3 min | 76 | 16 | 17% | 25 |
| fixed_usc_pepperdine | 3 min | 138 | 89 | 39% | 18 |
| broadcast_side_rally | 8 s | 12 | 0 | 0% | 3 |
| broadcast_back_view | 14 s | 16 | 2 | 11% | 3 |
| broadcast_side_high_women | 6 s | 4 | 1 | 20% | 0 |
| broadcast_side_high_men | 5 s | 1 | 1 | 50% | 0 |
| broadcast_back_rally | 8 s | 0 | 0 | | |

broadcast_back_rally has no calibrated camera (no usable court in its shot). Rejection does not follow the court's line
evidence (hawaii_pennstate has the best-supported court and the most rejections), which points at the 2D ball track.

## Player anchors under realistic conditions: a stress test (2026-10-13)
`scripts/eval_trajectory_synthetic.py --stress --seeds 20`: the ablation's corrupted detections (30% missed in bursts,
12% false, 2 px), robust fit with and without anchors, under conditions the ablation did not test. Median 3D error (m)
of the attack, and anchors on the wrong player:

| Condition | Without anchors | With anchors | Wrong anchors |
|---|---|---|---|
| Touching player only, 0.3 m off (the ablation's setting) | 0.76 | 0.32 | 0 / 140 |
| Twelve players in a match formation, toucher 0.3 m off | 0.76 | 0.40 | 20 / 140 |
| Twelve players, toucher 0.6 m off | 0.76 | **3.91** | 67 / 140 |
| Twelve players, toucher 1.0 m off | 0.76 | **5.37** | 76 / 140 |
| Twelve players, 0.6 m, camera slightly off (f +3%, 0.3 m) | 0.68 | **3.90** | 61 / 140 |
| Twelve players, 0.6 m, the system's own segmentation | 3.08 | 1.68 | 29 / 45 (48 of 80 flights not matched) |

**The published gain depends on who is near the ray.** With only the touching player as a candidate the anchor is
always right; with twelve players and a toucher position off by 0.6 m (easily reached on real footage: court error,
jumping, foot position), half the anchors pick another player, often a blocker or a teammate along the ray, which is
exactly the depth direction the anchor was meant to fix, and the attack error grows fivefold over the unanchored fit.
Under these detection errors the segmentation itself fails on most flights, with or without anchors.

A prototype that anchors only when the nearest player is clearly nearer than the second (prototype, not in the code):

| Condition (attack) | Without anchors | Margin 0.5 m | Margin 1.0 m |
|---|---|---|---|
| Twelve players, 0.3 m | 0.76 | 0.59 | 0.76 |
| Twelve players, 0.6 m | 0.76 | 0.59 | 0.76 |
| Twelve players, 1.0 m | 0.76 | 1.11 | 0.76 |
| Twelve players, 0.6 m, camera off | 0.68 | 0.61 | 0.68 |

A 1 m margin never makes the fit worse but seldom anchors; 0.5 m keeps a smaller gain (about 20% on the attack) up to
0.6 m of position error. The claim "anchors cut the attack error by 59%" holds only for an unambiguous toucher.
