# PRD: Court registration

Parent: [README.md](README.md) · OpenSpec: `openspec/changes/add-court-registration/`

## Problem
Landing points, in/out calls and which side won all require knowing where an image point lies on the real court. The capstone needed four manual clicks and only worked for a fixed camera. Pure geometry (finding white lines) latches onto ad boards and railings in broadcast footage: usable on only 1 of 5 clips.

## User stories
- As a coach, after uploading a video the court is found automatically; I don't click anything.
- As a coach, when the court is wrong I can drag the corners on one frame, and every landing in that part of the video updates.
- As a researcher, I can see how reliable each part's court estimate is; unreliable parts are never silently used for scoring.

## Requirements
**Functional**
1. Detect the 14 court keypoints (end line, attack lines and centre line on both sidelines, plus the net band); layout in `src/vball/court_keypoints.py`.
2. Produce an image ↔ court-metres mapping for every camera shot, following the camera when it moves within a shot (common in broadcast).
3. Attach a quality score to every mapping; parts below threshold are marked "needs review".
4. The user can correct a shot's court; the correction wins over the model and survives reruns.
5. Without a trained model, the system says "court model not ready" instead of pretending.

**Non-functional**
- Court stage time ≤ 0.5 × video duration on an M1 Pro CPU.
- Works from a single view; no camera parameters required from the user.

## Acceptance criteria
- k6y7r test split: median corner error < 0.3 m in court coordinates.
- VNL external split (broadcast camera unseen in training): median error of the 4 front-zone corners < 0.5 m; if missed, report the real number and add it to M4/M5 improvements.
- At least 4 of the 5 evaluation clips show a visually correct court overlay (currently 1 of 5).
- After correcting corners and rerunning the analysis, the correction is still in effect.

## Out of scope
- Lens distortion correction (see Unified Sports Field Registration, CVPRW 2026).
- 3D camera calibration from the net points (the data supports it; kept for 3D research).

## Dependencies
- `court_kpt_yolo26n.pt` trained on Colab (`notebooks/train_court_keypoints.ipynb`).

## Open questions
- Quality threshold values are chosen after training, from the error distribution (does not affect specs or UI).
