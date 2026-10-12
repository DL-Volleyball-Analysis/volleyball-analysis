# Moving cameras: court, players and 3D on footage where the camera pans and zooms

Version 1.0 · 2026-10-12 · Owner: YuJia Liang · Parent: [court-registration.md](court-registration.md)

## Why
The four 4K test videos (fan and club recordings) are filmed by a camera that pans to follow play and zooms in and
out; broadcast footage pans too. The system assumed a still camera within a shot in three places:

| Where | Assumption | Effect |
|---|---|---|
| Court smoothing | median of court corners over neighbouring samples | during a pan the median lags behind the camera |
| Court corrections | the user's four points hold for the whole shot | one correction is wrong as soon as the camera moves, so a correction cannot rescue a panning video |
| 3D flights | one camera calibration per shot, from the sample nearest its middle | flights far from that moment are reconstructed with the wrong camera: 15 of 33 flights on the Hawaii clip were rejected as impossible (43 m/s) |

Users film with phones and club cameras that move; a coach expects one court correction to be enough.

## What
1. Camera motion between frames (image-to-image homography) estimated from the whole frame while the video is
   decoded, with no labels and no extra decoding pass.
2. Court samples smoothed in a motion-compensated way (neighbouring samples are warped to the sample's frame before
   the median), and gaps without a detected court filled from the nearest detected samples.
3. A court correction follows the camera through its shot.
4. 3D flights calibrated per flight: the court sample nearest the flight is warped to the flight, and the ball
   track is expressed in that frame's image, so a pan during a rally no longer breaks the reconstruction.

## Success
- On a still camera the estimated motion stays still (photometric difference after warping no worse than without).
- On panning clips, warping a frame by the estimated motion lowers its photometric difference to a frame 1 s later.
- Fewer physically impossible flights on the Hawaii clip with the same court and ball results.
- One correction on a panning shot gives a court that stays on the lines (checked by eye on the 4K clips).

## Out of scope
Lens distortion; cameras that translate a lot (handheld walking): the image-to-image homography is exact only for a
camera that rotates and zooms about a fixed point, and for points on the floor plane.
