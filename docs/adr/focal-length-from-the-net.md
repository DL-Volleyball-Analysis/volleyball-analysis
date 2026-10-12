# Focal length from the net tape on symmetric end-line views

Date: 2026-10-12 · Status: accepted

## Context
3D ball flights need a calibrated camera (focal length and pose). From the floor alone, the focal length follows from
the homography under a zero-skew, square-pixel camera, but when the camera looks straight down the court's long axis
(a centred end-line view) that constraint degenerates: many focal lengths explain the floor equally well, and the
calibration either fails or returns a mirrored pose with the camera below the floor.

## Decision
Use the net, whose height is known (2.43 m men, 2.24 m women): for a range of focal lengths (0.3-5 image widths),
compute the pose from the floor homography with one consistent scale, project where the net tape would be, and score
how well the image supports a tape there (floor lines masked, top tape weighted over the lower band). The focal
length is the median of the near-best candidates. Calibration then also starts from several focal lengths and drops
poses with the camera below the floor (`court_lines.focal_from_net`, `calibration`).

## Consequences
- All six fixed clips calibrate, with plausible camera positions; 3D flights exist on fixed end-line views for the
  first time.
- Men's and women's heights are not told apart from the image; the projection of both is checked instead.
- Depends on the net being visible and unobstructed in the background plate.

## Alternatives
- Assume a typical focal length: wrong by large factors across phones and camcorders.
- Use vertical structures (walls, posts): not standardised, often absent from the view.
