# Research directions (2026-10-11)

Where the project stands against published work, what is a research contribution and what is engineering, and
what to do next about the two weakest results: 3D ball trajectories and keeping only players.

## 1. Diagnosis: why the 3D trajectories fail on real footage

Measured on the two high side views, the only clips with an ok court (`docs/results/court-keypoints.md`):

| | women (court model v2) | men (court model v3b) |
|---|---|---|
| Camera calibration | ok: 3.8 px, focal sd 3%, camera at (8.8, -17.2, 6.2) m | unusable: focal sd 15% |
| Ball detected | 67% of frames | 28% of frames |
| Segmented flights | 6, 8-24 frames each | 3 |
| Fit | 20-128 px median residual, starts near the camera | 3.7-172 px, up to 26 km/s |

Three causes, in order of importance:

1. **The 2D ball track.** Missed and false detections cut flights into short pieces that mix the ball with
   other objects, so no ballistic path explains them (residuals of 20-170 px against 4 px allowed).
2. **An unconstrained fit collapses toward the camera.** From one view a near, slow ball and a far, fast ball
   project alike; with nothing ruling out the near solution, several fits start a few metres from the camera.
   The synthetic tests never hit this because their tracks are clean.
3. **Calibration on some views.** The men's clip has collinear-looking floor points from its angle; the focal
   length is not determined (the gate correctly refuses it).

## 2. Published work

### Monocular 3D ball trajectories
- **Physics fit with court calibration** (ours; also Chen et al. for volleyball replay, and the table tennis
  works TT3D 2025 and *Uplifting Table Tennis* 2025): ballistic or drag/spin models fitted to 2D detections.
  Accurate when the track is clean and long; ambiguous along the line of sight for short flights.
- **Learned uplifting**: *Where Is The Ball* (Ponglertnapakorn and Suwajanakorn, CVPRW 2025) trains an LSTM on
  simulated trajectories only, with a camera-independent canonical 3D representation and reprojection
  consistency, and reports state of the art on synthetic and real data. Our synthetic rally generator
  (`vball.trajectory.synthetic`) already produces this kind of training data.
- **Geometric constraints for volleyball**: *Monocular 3D Volleyball Trajectory via Geometric Constraints*
  (Springer, 2026) reprojects 2D positions under court constraints for a 360° replay.
- **Context the physics fits ignore**: who touched the ball and where they stand. In volleyball every flight
  starts and ends at a player's hands, a block, the net or the floor.

### Keeping only players
- **SportsMOT** labels only players on the court; referees, coaches and spectators are distractors by design. A
  detector fine-tuned on its volleyball training sequences learns to leave them out (e.g. an RT-DETRv2 fine-tuned
  on SportsMOT as a single "player" class). Volleyball has at most 12 players on court, a hard cap per frame.
- **Team clustering**: crops embedded with SigLIP, reduced with UMAP and clustered with k-means into the two
  teams (Roboflow's basketball and football pipelines); people who fit neither cluster (referees, line judges)
  are outliers. The libero wears a different colour and must not be dropped: use position on court as well.
- **Court masks** (ours): people standing outside the court area are dropped; this only works when the court
  is found, and the first referee stands on the stand at the net post, inside the free-zone margin.

### Ball detection (2D)
TrackNetV3 (NYCU) adds trajectory rectification (inpainting missed frames), TrackNetV4 (ICASSP 2025) motion
attention, TrackNetV5 (NYCU, 2026) for badminton and tennis; BlurBall (CVPRW 2026) models motion blur. VballNet,
used here, is a volleyball-tuned TrackNet variant. None is measured on our footage with labels yet.

## 3. What is a contribution here, and what is engineering

Engineering (useful, not novel): the staged pipeline, the review app, training standard detectors.

Candidates for a research contribution, strongest first:

1. **Player-anchored monocular 3D ball trajectories with uncertainty.** Constrain each flight's ends with the
   court positions of the players at the touches (from the homography and player tracking), the net, and the
   floor, inside a physically bounded fit, and report per-flight uncertainty. This attacks exactly the
   line-of-sight ambiguity that makes short attacks unrecoverable from one camera, and it needs the full system
   (court, players, ball) that this project already has. Compare against the unconstrained physics fit and a
   learned uplifting baseline trained on our simulator.
2. **A real 3D ground truth for volleyball from two phones.** Record team practice with two synchronised phones,
   triangulate the ball, and evaluate single-camera methods on it. Public volleyball data has no 3D ball labels;
   this makes every 3D number in this project a measurement instead of a synthetic result.
3. **Label-free model selection for court registration.** Choosing among court models per shot by the agreement
   of floor and net keypoints (already built) is a small but clean idea: a self-check that needs no labels.

Fit with NTHU: Prof. Hu Min-Chun's lab works on sports video analytics, event detection and 3D replay
(basketball, table tennis); Prof. Chu Hung-Kuo's on 3D reconstruction. Directions 1 and 2 sit between the two.

## 4. Plan (each item becomes a PRD + OpenSpec change before implementation)

| # | Change | What | Measure |
|---|---|---|---|
| A | `filter-on-court-players` | Fine-tune the player detector on SportsMOT volleyball train (players only) on Kaggle; cap at 12 players; team clustering with outliers for referees as a second filter | IDF1 / HOTA on SportsMOT val (now 0.484 / 0.467; oracle filter 0.622) |
| B | `constrain-3d-flights` | Bounded fit (inside the hall, above the floor, speed limit), player-anchored touches, robust segmentation (drop outliers by residual), net-crossing check | synthetic with false detections added; share of real flights kept and plausible |
| C | `measure-ball-2d` | Label ~500 frames of our clips; compare VballNet with TrackNetV3/V4 | detection F1 within 5 px |
| D | `two-camera-ground-truth` | Capture protocol and triangulation for real 3D labels | 3D error of B on real flights |

Order: A and B first (both fix visible problems and B is the research core), then C, then D once footage of
the team's own matches exists.

## Sources
- Ponglertnapakorn and Suwajanakorn, *Where Is The Ball: 3D Ball Trajectory Estimation From 2D Monocular
  Tracking*, CVPRW 2025. https://arxiv.org/abs/2506.05763
- *Monocular 3D Volleyball Trajectory via Geometric Constraints*, Springer 2026.
  https://link.springer.com/chapter/10.1007/978-3-032-22592-4_17
- *TT3D: Table Tennis 3D Reconstruction*, 2025. https://arxiv.org/pdf/2504.10035
- *Uplifting Table Tennis*, 2025. https://arxiv.org/pdf/2511.20250
- *Real-time Localization of a Soccer Ball from a Single Camera*, 2025. https://arxiv.org/pdf/2506.07981
- SportsMOT and the challenge's player-only rule: https://codalab.lisn.upsaclay.fr/forums/4433/523
- RT-DETRv2 fine-tuned on SportsMOT: https://huggingface.co/smallTech/rtdetr-sportsmot
- Team clustering with SigLIP, UMAP and k-means: https://blog.roboflow.com/identify-basketball-players/
- Papers already in `papers/` (TrackNet V3-V5, BlurBall, VNL-STES, PnLCalib, unified field registration).
