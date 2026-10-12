# Design

## Background plate
Per shot with a still camera (camera motion moves the image centre by less than 1% of the width over the shot): the
per-pixel median of 60 frames spread evenly over the shot. Players, ball and referees move, so the plate shows the
empty floor. Shots with a moving camera keep the keypoint fit (phase 2).

## Line pixels
At a working width of 1280 px. A pixel is a line pixel if it is brighter by t (18 grey levels) than the pixels tau
(6 px) away on both sides, horizontally or vertically (Farin et al.); a second pass with the image inverted finds dark
lines (some multi-sport floors paint volleyball lines black). Connected parts that are short or fill their bounding box
(text, logos, wood grain) are removed.

## Court fit
Hough segments are merged into lines (angle within 2 deg, distance within 8 px) and split into two direction families
(within 25 deg of horizontal, or steeper). A hypothesis takes two lines of one family as the sidelines (y = 0, 9) and
two lines of the other as cross lines at court positions x in {0, 6, 9, 12, 18} (all ordered pairs), for both family
roles; the homography follows from the four intersections. Rejected: implausible courts (`court_is_plausible`), courts
under 8% of the image, and fans or slivers (an interior angle under 25 deg or a side under 10% of the width).

Score: the seven court lines are sampled every 6 px inside the image; a sample is supported within 3 px of a line
pixel (distance transform). Score = supported - 0.5 x unsupported + 200 x (lines with at least half their samples
supported and longer than 5% of the width). The per-line term stops a court squashed onto one stripe from winning.

## Registration
For still shots: the line fit and the keypoint fit (median over the shot's samples) are scored on the same plate; the
higher score wins and becomes every sample of the shot (`source`: "lines" or "keypoints"). Status ok when the winning
fit has at least 5 well supported lines and at least 70% of its samples supported; thresholds set on the broadcast
clips and the first three fixed clips, checked on the other three.

## Evaluation
One labelled frame per fixed clip (four corners or the near half, entered with the web app's court tool) gives the
error in court metres for the whole clip. Broadcast clips: status and overlays before and after.

## Risks
Floors with many white lines of other sports; the per-line support term and the volleyball line spacing (0, 6, 9, 12,
18 m) usually separate them, as on the GCU and UCLA floors. Cost: the search takes 1-70 s per shot on this machine;
once per shot, not per frame.
