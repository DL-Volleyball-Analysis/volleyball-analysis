# Design

## Context

- `vball.trajectory`: segmentation by image-velocity jumps, ballistic fit p(t) = p0 + v0 t + g t^2 / 2 by robust
  least squares from 9 starts, depth sd from the Jacobian, quality gates, and since 2026-10-11 a rejection of
  impossible fits (speed > 40 m/s or leaving the hall).
- Real evaluation (docs/research/directions.md): women's clip calibrates (3.8 px, camera 17 m from the near
  sideline, 6 m up); 67% of frames have a detection; flights of 8-24 frames; residuals 20-128 px; several fits
  start near the camera. Men's clip: calibration refused (focal sd 15%), 28% detection.
- Players table: court_x / court_y per track and frame when the court is ok.

## Goals / Non-Goals

**Goals:** real flights that survive; each constraint's effect measured. **Non-Goals:** drag / spin models,
learned uplifting, better 2D detection.

## Decisions

### Error model for synthetic rallies
`vball.trajectory.synthetic.corrupt(uv, miss, false, noise_px, seed)`: drop a share of detections (in short bursts,
as occlusions are), replace a share with uniform points in the image and add Gaussian noise. Rates are measured on
the evaluation clips' ball tracks against their fitted flights (miss from the detection rate; false from
residuals above 30 px), then used in the ablation.

### Robust refit
Fit, compute residuals, drop detections above max(3 x median residual, 8 px), refit; at most 3 rounds. Removal is
reported (`dropped`). This replaces relying only on the Huber loss, which cannot recover when a third of a short
flight is wrong.

### Bounds
`least_squares(..., bounds=...)` on p0 inside the hall box (x in [-m, 18+m], y in [-m, 9+m], z in [r, H]) and
v0 inside the speed limit per axis; positions along the flight are checked after the fit (the box on p0 alone does
not bound the whole arc) and a violation marks the flight low quality ("on a bound"). The 9 initialisations stay;
the near-camera start heights are excluded because the rays are cut at the hall boundary.

### Player anchors
At the first and last frame of a flight, take the players placed on court in that frame (players.csv.gz), the
nearest to the ball's ray (smallest horizontal distance between the ray's points at heights 0.5-3.5 m and the
player's court position). If within 2.5 m, add residuals (p_xy(t_end) - player_xy) / sigma with sigma = 1.0 m. A
touch at the net or the floor is not anchored to a player (the floor is already the floor contact in derived
values). Anchors are reported per flight (`anchors: ["start" | "end"]`).

### Order in the stage
segment -> for each flight: bounded fit -> robust refit -> anchored refit (if players) -> quality and
impossibility checks. The trajectory stage reads players.csv.gz (it already runs after players).

## Risks / Trade-offs

- [A wrong anchor (nearest player is not the toucher)] → radius 2.5 m and a soft prior (sigma 1 m); the
  ablation reports the share of wrong anchors in synthetic rallies with several players near the ball.
- [Bounds hide a bad calibration] → a solution on a bound is low quality, never ok.
- [Rates measured on two clips] → stated with the results; recomputed when more footage arrives.
