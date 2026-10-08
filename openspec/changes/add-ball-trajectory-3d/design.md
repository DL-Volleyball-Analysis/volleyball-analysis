# Design

## Context

- Court keypoints: 14 points, 10 on the floor and 4 on the net band (`vball.court_keypoints.k6y7r_points_3d`, net top 2.43 m men / 2.24 m women). A scratch check on the labels already recovered plausible cameras (median height ~4.6 m) from the floor homography plus the net points.
- Court samples per shot come from `add-court-registration` (5 per second, corners per sample); broadcast cameras pan and zoom within a shot.
- Ball track: one image position per frame or a miss (`vball.ball`), typically 30-60 fps.

## Goals / Non-Goals

**Goals:** a physically constrained single-camera reconstruction whose errors are measured (synthetic) and visible (per flight); a UI that never shows a guessed path as certain.
**Non-Goals:** spin and drag modelling beyond an optional linear drag term; touch classification.

## Decisions

### Module ownership
| Responsibility | Module |
|---|---|
| Intrinsics + pose from keypoints, reprojection error, quality gate | new `vball.calibration` |
| Flight segmentation, ballistic fit, derived values, quality | new `vball.trajectory` |
| Synthetic arcs through a known camera (tests and evaluation) | `vball.trajectory.synthetic` |
| Stage wiring, `flights.json`, API | web app `pipeline.py`, `main.py` |
| 2D board (SVG) and 3D board (three.js) | web app `src/board/` |

### Calibration: homography-initialised, refined on all points
Principal point at the image centre, square pixels, no distortion. Initialise the focal length from the floor homography (zero-skew constraint), get the pose with `solvePnP` on the floor points, then refine focal length and pose together with SciPy `least_squares` on every visible keypoint, net points included (they make the problem non-planar). Try both net heights and keep the lower reprojection error; a match-level setting can pin it. One calibration per court sample, so panning and zooming are followed; a flight uses the calibration of the samples around it.
*Alternative:* `cv2.calibrateCamera` on one view. Rejected: it needs a good intrinsic guess anyway and offers less control over which parameters are free.

### Flights
Smooth the image track lightly, compute velocity, and cut where the direction changes by more than a threshold angle or the speed jumps, and where the ball is missing for more than a few frames. Flights shorter than a minimum length are not reconstructed. The events stage may later replace these cuts with confirmed touches.

### Ballistic fit
Unknowns per flight: start position p0 and velocity v0 (6 values); p(t) = p0 + v0 t + ½ g t² with g = (0, 0, −9.81). Minimise image reprojection residuals with a robust (Huber) loss, several initialisations (rays of the first and last detections at heights 1, 2 and 3 m), keep the best. Optional linear drag (one extra parameter) is compared on real flights; it stays off unless it lowers the fit error meaningfully.

### Quality
Fit error = median reprojection residual in pixels. Depth conditioning from the fit's Jacobian: if the uncertainty of position along the camera ray exceeds a threshold, the flight is low quality ("depth poorly constrained"). Both thresholds are configuration, tuned on synthetic and real flights.

### Storage and API
`flights.json`: per flight its frames, parameters, fit error, quality and reason, derived values. 3D positions are computed from the parameters on request (cheap), so the API `GET /videos/{id}/flights?start=&end=` returns flights with positions sampled per frame and an observed / not-observed flag.

### UI
- 2D board: reuses `court/geometry.ts`; ground tracks as polylines, height as a single-hue sequential colour with labels at apex and net crossing (never colour alone), landing marks as in the court map, players from `/players` when present.
- 3D board: three.js with orbit controls, loaded with a dynamic import when its tab opens so the main bundle does not grow; net drawn at the calibrated height.
- Both read playback time from `playback/clock.ts` in an animation frame to place the ball marker, like the overlay canvas.

## Risks / Trade-offs

- [Court model accuracy limits calibration] → Calibration quality gate; reprojection error reported; flights from unusable shots are not reconstructed.
- [Short flights or flights along the line of sight are ambiguous] → Depth conditioning flag; dashed in the UI.
- [Men's vs women's net height] → Both tried, lower error wins; match setting can pin it.
- [three.js size] → Lazy-loaded tab.

## Migration Plan

New stage after `players`; the events stage version is bumped again so it recomputes after trajectory. Archive this change after `add-player-tracking` (same stage-order requirement).

## Open Questions

- Default thresholds (flight cut angle, fit error, depth uncertainty) are set from the synthetic and real measurements in the tasks; they do not change the specs.
