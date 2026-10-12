# Design

## Motion estimation
Frames are converted to grey at 640 px width. A keyframe gets up to 600 Shi-Tomasi corners. Each new frame is
registered to the keyframe directly (pyramidal Lucas-Kanade, initial positions from the previous frame's
keyframe-to-frame homography, RANSAC homography with a 1 px threshold at 640 px), so errors do not accumulate frame by
frame while the keyframe stays valid. When the inlier share drops below 0.5 (players and crowd moving, large pan,
cut), the previous frame becomes the keyframe. Output per frame t >= 1: the step homography frame t-1 -> t in full
resolution pixels and the inlier share; frame 0 has the identity. A step with no estimate is the identity with share 0.

The frame a -> frame b mapping is the product of the steps in between (inverse products for b < a). A prototype that
chained frame-to-frame estimates instead drifted on a still camera (side rally clip: photometric difference 12.6 ->
19.7 after warping); the keyframe version keeps it at 12.6 and lowers the difference on the panning 4K clips by 30-40%.

## Court
- Smoothing: for sample i, every valid sample j in the window is warped to frame i (its corners through the motion
  j -> i) before the per-corner median. Without motion, the old median.
- Gap filling: sampled frames without a valid court get the corners of the nearest valid sample warped to them, if
  that sample is at most `max_fill_s` (5 s) away. Filled samples are marked `filled` and do not count as valid for
  the shot status.
- Corrections: the corrected sample is warped to every sampled frame of its shot; its keypoints (floor and net) are
  warped with it (exact for a camera that rotates and zooms).

Samples keep their format (frame, corners, keypoints), so the frontend, `corners_at` and the renderer need no change.

## 3D
Per flight: reference frame r = the flight's middle frame. The nearest sample's 14 keypoints are warped to r and
calibrated; ball positions of the flight's frames are warped to r's image. Fitting runs in r's image. Flights are
still found by `trajectory.segment` on the shot's track, which is now also expressed in one reference image per
segment so a pan does not look like ball motion.

## Risks
Players and crowd dominate the features on tight shots; the keyframe RANSAC copes when the background keeps at least
half the features. The homography is exact only for rotation and zoom; a translating camera makes floor and stands
disagree, and RANSAC follows the larger group.
