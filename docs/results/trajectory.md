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

## Real footage
Not measured yet (tasks 1.3, 8.1): calibration reprojection error on the k6y7r test labels and with
court model predictions, and net-crossing heights on the evaluation clips.
