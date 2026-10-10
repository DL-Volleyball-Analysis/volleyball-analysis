# Design

## Context

- The keypoint layout and its 3D coordinates are defined in `src/vball/court_keypoints.py` (14 points; 0-9 on the floor, 10-13 on the net band). Training happens on Colab and produces `court_kpt_yolo26n.pt`.
- The `decode` stage already splits a video into camera shots; the pipeline runs stages in order and reuses results by version (`openspec/specs/analysis-jobs`).
- Evaluation clips are broadcast footage whose cameras pan and zoom within a shot; the user's own gym footage is expected to be mostly tripod-mounted.
- `vball.court` owns the court frame and the `to_image` / `to_court` helpers. `vball.court_geometry` (line-based) stays as an experimental fallback and is not used by this change.

## Goals / Non-Goals

**Goals:**
- A per-frame mapping that is cheap to evaluate anywhere in a shot, from a model run on a subset of frames.
- Pure, unit-testable geometry (fitting, sanity checks, smoothing, interpolation) separated from model inference.

**Non-Goals:**
- Using the net-band points for full camera calibration (kept in the data model, unused here).
- Choosing the final quality thresholds; they are configuration, tuned after the evaluation runs.

## Decisions

### Module ownership
| Responsibility | Module |
|---|---|
| Keypoint inference: frame → 14 × (x, y, confidence) | `vball.court_keypoints.detect` |
| Homography fit from keypoints, sanity checks, error | `vball.court_keypoints.fit_homography` |
| Per-shot sampling, smoothing, interpolation, status | new `vball.court_registration` |
| Stage wiring and storage of `court.json` | web app `pipeline.court` |
| Corrections table and court endpoints | web app `database.py`, `main.py` |
| Evaluation in metres | new `scripts/eval_court_keypoints.py` |

The web app never fits homographies itself; it stores and serves what `vball` returns, and resolves corrections at read time.

### Court model v3: training data and model (2026-10-08)
Measured v2 (YOLO26n-pose, 960 px, 300 epochs, correct flip_idx), end to end (homography from points with
confidence ≥ 0.5 + RANSAC, labelled points mapped to court metres): k6y7r test median 0.49 m, p90 3.37 m,
23% of images without a fit; VNL median 1.35 m on every clip, 39% without a fit. VNL errors are systematic:
the model places the attack lines ~4.8 m from the centre line instead of 3 m on the VNL court paint.
v3 changes the data and the model, not the pipeline:
- **VNL labels completed by geometry.** The 4 labelled front-zone corners give an exact homography of the
  floor; projecting the standard court gives the other 6 floor points (points outside the image are
  invisible). Checked on k6y7r, where full labels exist: completing from the 4 front-zone corners
  reproduces the other labelled floor points with a median error of 2.1 px (p90 10.3 px) on 640 px images.
- **VNL net points are left unlabelled.** Projecting them through a per-frame calibration was tried:
  on k6y7r the projected net points are off by 5.3 px median but 29.4 px p90, and on VNL the focal length
  estimated from the front zone varies 6-16% within a clip, which could not be told apart from zoom, and
  the projected net could not be confirmed by eye. Unlabelled (visibility 0) teaches the model that the
  net points are not visible on these frames; the alternative, possibly wrong labels, was judged worse.
  Net points matter for 3D calibration, which has a floor-only fallback. Training must not degrade net
  points on gym footage: v2 and v3 net-point errors on the k6y7r test split are compared.
- **Split VNL by clip**, not by frame: clips one, two, three for training (every 2nd frame, so VNL does
  not outweigh the 347 k6y7r images), clips four and five held out as `test_vnl`. The held-out clips share
  the broadcast with the training clips, so they are not unseen cameras; the external test remains our
  own gym footage (M5).
- **Bigger model, larger input, longer training:** YOLO26s-pose at 1280 px for 400 epochs (v2 was still
  improving at epoch 300; far court lines are thin at 960 px).
- The court box of VNL images is recomputed from the completed points, so ultralytics' box/pose metrics
  on VNL become meaningful; the end-to-end metre error stays the deciding metric.

### Line refinement after the model
Starting from the model's homography (about 1 m off), search for the painted court lines near their
predicted image positions (edge points along the projected lines, robust line fit) and re-fit the
homography to the line intersections. Starting near the answer is what the pure geometric detector
lacked (it latched onto ad boards from scratch). A refinement that moves the corners by more than a
bound or raises the line residual is discarded and the model's homography kept.

### Sample, then interpolate corners (not homographies)
Run the model at 5 samples per second of video, not every frame: about 6x fewer inferences, and court motion between samples is smooth. A frame between two samples gets its mapping by linearly interpolating the projected positions of the four court corners and re-fitting the 4-point homography. Interpolating matrix entries directly is not well-behaved under perspective; corner interpolation is, and it is what the eye sees.
*Alternative considered:* one homography per shot. Rejected because broadcast cameras pan within shots (spec scenario "Panning broadcast camera").

### Fit with RANSAC on floor points, confidence-filtered
Use only floor keypoints 0-9 with confidence ≥ a threshold, at least 4 of them, `cv2.findHomography(..., RANSAC)` with a reprojection threshold proportional to the image diagonal. The net points are above the floor and would bias a planar fit.
*Error estimate:* the median reprojection error of all confident floor points, divided by the image diagonal, so it is comparable across resolutions. (Changed from the inliers' RMS during implementation: with very noisy points RANSAC can keep exactly four, which a homography fits perfectly, so the noisiest frames reported the smallest error.) A small error means the points agree with each other, not that they are right: on the evaluation clips, three views from behind an end line reported small errors with the whole court squeezed into the near half (`docs/results/court-keypoints.md`).

### Geometric sanity before accepting a fit
Reject a fit if the projected court corners are not a convex quadrilateral with the same handedness as the training labels (camera above the floor), or if the projected court covers less than 2% of the image. A rejected fit counts as "no estimate" for that sample.

### Temporal smoothing within a shot
Per corner, take a running median over 5 consecutive valid samples, never across a shot boundary; near the ends of a shot the window shrinks on both sides so it stays centred (a one-sided window pulled a panning camera's first and last samples toward their neighbours by half a sample). This removes single-sample jumps without lagging behind real pans much (5 samples = 1 s).

### Shot status
- `failed`: fewer than 2 valid samples in the shot.
- `needs_review`: median error above the configured threshold, or fewer than half of the samples valid.
- `ok`: otherwise.
Thresholds live in one config dict in `vball.court_registration` and are tuned after the first evaluation.

### Stored format
`court.json` keeps, per shot: status, error, corrected flag, and samples `{frame, corners_px[4][2], error, keypoints[14][3]}`. Corners rather than matrices: they are what gets interpolated and drawn, they are readable, and the homography is cheap to rebuild. The raw keypoints are kept because camera calibration (`add-ball-trajectory-3d`) needs the net points, which the floor homography ignores.

### Corrections resolved at read time
Corrections live in a new SQLite table `court_corrections(video_id, shot_idx, frame, corners_px)` and are never written into `court.json`. Anything that reads the court (API, events stage) goes through one function that overlays corrections on the stage result. This is what keeps corrections intact across reruns.
*Alternative considered:* writing corrections into `court.json`. Rejected: a rerun of the court stage would overwrite them.

### Correction triggers events onward
Saving or clearing a correction queues a job from `events` (see delta in `specs/analysis-jobs`). Ball tracking does not use the court, so it is reused.

### Model runtime
Load the `.pt` weights with ultralytics (already a dependency). The PRD budget (court stage ≤ 0.5 × video duration) at 5 samples/s allows up to 100 ms per inference on the M1 Pro CPU; inference time has not been measured yet and is checked in the tasks. ONNX export is deferred until the web app needs to drop torch or the budget is missed.

## Risks / Trade-offs

- [Training data has few gym tripod views or unusual angles] → The evaluation reports the VNL split separately; user corrections cover failures; misses feed the next dataset round.
- [Corrections assume a static camera within the shot] → For a panning shot, a correction pins the mapping to one frame. Accept for M1 because own footage is tripod-based; flag panning shots in the court-check UI later.
- [5 samples/s misses very fast zooms] → Sample rate is configuration; the error estimate exposes bad interpolation.
- [Thresholds picked before data] → Kept as configuration and tuned once the evaluation exists; no spec depends on their values.

## Migration Plan

The court stage version changes from `0` to `1`, so existing videos recompute court and the later stages on their next analysis. No data migration: the corrections table is new.
