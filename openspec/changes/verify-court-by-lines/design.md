# Design

## Line evidence
A ridge map: white top-hat of the luminance (kernel about 2x the expected line width at that image row, from the
mapping's scale), thresholded per frame by percentile. Court lines from `vball.court` (sidelines, end lines, centre,
attack lines) are sampled every ~10 px in the image; a sample is supported if the ridge map is on within +-3 px
perpendicular to the line. Players occlude lines, so support is a share, not all-or-nothing; lines outside the image
or under the scoreboard band are skipped.

## Refinement
Start from the keypoint homography; perturb the four image corners (coarse-to-fine, Nelder-Mead or a small grid) to
maximise support with a penalty on the keypoint residual, so the fit cannot drift to other lines. Run per sampled
frame, then take the shot's median homography as today.

## Evaluation
Labelled: k6y7r test and VNL held-out clips. Per image: keypoint fit error in metres (existing script), line support
before/after refinement. Report ROC AUC of support for "error < 0.5 m", the threshold chosen on the training images,
and error before/after refinement. Unlabelled: the nine videos, overlays checked by eye.

## Risks
Multi-sport floors have lines of the right width and colour; the check then only helps when the wrong mapping lands
off lines. Strong motion blur lowers support; the median over a shot's samples absorbs single frames.
