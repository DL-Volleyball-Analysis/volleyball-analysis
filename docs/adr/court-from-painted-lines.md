# Court from painted lines for still cameras

Date: 2026-10-12 · Status: accepted

## Context
Amateur and college matches are often filmed from a fixed camera behind an end line. Both court keypoint models
(trained on gym images and on broadcasts) failed on all six fixed end-line clips: they squeezed the court into the
near half (docs/results/court-keypoints.md). Players stand on the lines during play, so any single frame shows only
part of them, and there are no labelled end-line images to train on.

## Decision
For a camera shot that does not move (`vball.camera_motion`), build a background plate as the median of frames over
the shot, so players disappear and the painted lines are whole. Find line pixels with a width-tuned test that keeps
thin bright or dark lines, group line candidates into two directions, and fit court models (two sidelines plus two
cross lines) to them, scored by how many line pixels they explain. Reject fits that no real camera could produce
(the court must be below the horizon, shapes and angles plausible). The line fit decides the shot's court when it is
well supported; otherwise the shot is marked needs_review (`vball.court_lines`, `court_registration.with_line_evidence`).

## Consequences
- 6 of 6 fixed clips get the right court by eye, without training data; error in metres is not measured yet (one
  labelled frame per clip is the next step).
- Works only when the camera is still and the lines are visible: on a light floor with thin white lines and on one
  arena with a shifted fit, it fails and correctly marks the shot needs_review (two of six full matches).
- Adds a few seconds per still shot; moving cameras keep the keypoint models.

## Alternatives
- Label end-line frames and retrain the keypoint model: no such data, and a new view type would need new labels again.
- Ask the user to click four corners for every video: kept as the correction path, not as the default.
