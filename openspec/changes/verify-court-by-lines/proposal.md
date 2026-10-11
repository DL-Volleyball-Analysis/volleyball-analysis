# Proposal

## Why

Six of the nine analysed videos have no usable court, so they get no court positions and no 3D flights. Inspection
(2026-10-12) found two different causes behind the same "needs review" status:

- **Correct courts rejected.** On the broadcast back and side views the floor fit lies on the court lines, but the
  check compares the model's net points with the calibrated net-top points above the sidelines, while the model puts
  them at the ends of the net about 1 m outside (posts and antennas). Net error 0.04-0.07 of the image width vs a
  threshold of 0.015.
- **Wrong courts caught, for the wrong reason.** On the 4K low end-line gym view the floor fit follows other sports'
  lines. A line-distance version of the net check would pass it (0.014), so the net alone cannot separate the cases.

The image itself can: a correct mapping puts the projected court lines on painted lines. Line evidence is the
standard check and refinement in sports field registration (e.g. Citraro et al. 2020; Theiner and Ewerth, TVCalib
2023; PnLCalib 2026), and needs no extra labels.

## What Changes

- `vball.court_lines`: a line-support score (share of points along the projected court lines that lie on a thin
  bright ridge in the frame) and a refinement of the homography that maximises it from the keypoint estimate.
- Court registration uses line support (with the floor fit error) to decide ok / needs review; the net check stays as
  a 3D (camera) check for calibration only.
- Measured on labelled court test sets (k6y7r test, VNL held-out clips): does line support separate fits under 0.5 m
  from worse ones (ROC AUC), and does refinement lower the error? Then on the nine videos.
- Phase 2 (only if low end-line views stay unsolved): perspective augmentation in court keypoint training (Kaggle) to
  cover low camera angles.

## Capabilities

### New Capabilities
- `court-verification`: line-evidence check and refinement of court mappings.

## Impact

New `src/vball/court_lines.py` and tests; `vball.court_registration` status rule; court stage version bump;
`docs/results/court-keypoints.md`. No new data needed for phase 1.
