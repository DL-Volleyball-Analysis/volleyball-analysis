# Proposal

## Why

None of the six fixed end-line camera clips (data/videos/fixed, five arenas) gets a correct court, so they have no court
positions and no 3D: both keypoint models were trained on side and broadcast views and squeeze an end-line view's
court into the near half. The net check passes such fits (0.007 on Hawaii vs Penn State), so wrong courts reach later
stages. Earlier inspection (2026-10-12) also found correct broadcast courts rejected by the same check.

A fixed camera sees the same floor for the whole video. The median of frames spread over a shot is an empty court (a
background plate: players, ball and referees disappear), on which the painted lines are clean. Fitting the court model
to those lines is the classic court registration approach (Farin et al. 2003/2004; line evidence also in Citraro et al.
2020, TVCalib 2023, PnLCalib 2026) and needs no labels and no training.

A first per-frame line-support score was tried (2026-10-12): ROC AUC 0.77 for "fit error < 0.5 m" on k6y7r test, but on
textured multi-sport floors it scored wrong courts higher than right ones. On a background plate with a stricter line
test it works: all six fixed clips fitted correctly by eye.

## What Changes

- `vball.court_lines`: background plate of a shot; line pixels (brighter, or darker, than the floor on both sides,
  elongated); line candidates from the Hough transform; a court model fitted by trying pairs of sidelines and pairs of
  cross lines with their court positions, scored by how much of every projected court line lies on painted lines;
  geometric checks (plausible, at least 8% of the image, no fans or slivers).
- Court registration: for shots where the camera is still (camera motion, change follow-camera-motion), the line fit
  from the plate is compared with the keypoint fit by the same line score; the better one is used for every frame of
  the shot. Status from line evidence (line score and the number of well supported court lines); the net check stays a
  calibration check only.
- Measured: the six fixed clips (labelled once per clip: a fixed camera needs one labelled frame), the five broadcast
  clips (no regression), court error in metres.
- Phase 2 (only if needed): moving cameras (line fit per sampled frame, players masked), perspective augmentation for
  the keypoint model.

## Capabilities

### New Capabilities
- `court-verification`: line-evidence court fitting and status.

## Impact

New `src/vball/court_lines.py` and tests; `vball.court_registration` and the court stage (version bump);
`docs/results/court-keypoints.md`. No training.
