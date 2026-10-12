# Proposal

## Why

Landing points, in/out calls and which side won a rally all need image points expressed in court metres. Today the court stage is a stub, the capstone needed four manual clicks per video, and the geometric line detector worked on only 1 of 5 broadcast clips. The court keypoint dataset (14 points, `src/vball/court_keypoints.py`) and the Colab training notebook are ready, so the learned model can now be wired in. Implements [docs/prd/court-registration.md](../../../docs/prd/court-registration.md) (milestone M1).

## What Changes

- Detect the 14 court keypoints with the trained YOLO pose model on sampled frames of each camera shot.
- Fit an image-to-court homography per sample, reject geometrically invalid fits, smooth over time within a shot, and give every shot a quality status.
- Store the court result as the `court` pipeline stage; when the model is missing the stage stays `unavailable` (current behaviour).
- Let the user correct a shot's court by placing the four corners; corrections survive reruns and trigger recomputation of later stages.
- Add an evaluation script that reports keypoint and corner errors in metres on the k6y7r test split and the external VNL split.

Out of scope: lens distortion, 3D camera calibration from the net points, the court-check UI (part of `rebuild-match-review-ui`), landing/rally logic (M3).

## Capabilities

### New Capabilities
- `court-registration`: mapping between image pixels and court metres for every frame of an analysed video, with quality status and user corrections.

### Modified Capabilities
- `analysis-jobs`: a court correction queues recomputation from the events stage (ball tracking does not depend on the court and is reused).

## Impact

- `src/vball`: keypoint inference, homography fitting and per-shot registration modules.
- Web app: `court` stage implementation, new court endpoints, a corrections table in SQLite.
- New runtime dependency for the pipeline: the trained weights `models/court_kpt_yolo26n.pt` (ultralytics is already installed).
- `scripts/`: evaluation script; `scripts/detect_court.py` switches to the learned model.
