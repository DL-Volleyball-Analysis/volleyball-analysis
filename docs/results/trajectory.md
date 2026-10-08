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
