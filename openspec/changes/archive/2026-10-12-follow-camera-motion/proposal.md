# Proposal

## Why

The 4K test videos and broadcast footage pan and zoom, but court smoothing, court corrections and 3D calibration
assume a still camera within a shot (PRD: docs/prd/moving-camera.md). The clearest symptom: on the Hawaii clip 15 of
33 flights are rejected as physically impossible because one camera calibration is used for a 64 s shot in which the
camera follows play.

## What Changes

- `vball.camera_motion`: frame-to-frame homographies estimated by keyframe tracking (corners tracked from a keyframe
  with pyramidal Lucas-Kanade, RANSAC homography; a new keyframe when the inlier share drops), and the mapping between
  any two frames of a shot.
- The decode stage stores the motion (`camera_motion.npz`) while it reads every frame for shot cuts.
- Court registration: motion-compensated smoothing; samples where no court was detected filled from the nearest
  detected ones (within a time limit); corrections propagated through their shot.
- 3D: per flight, the nearest court sample's keypoints and the ball track are brought into one frame of the flight
  before calibration and fitting.
- Measured: photometric difference with and without motion (still and panning clips), flights rejected on the
  Hawaii clip before and after.

## Capabilities

### New Capabilities
- `camera-motion`: camera motion estimation and its use by the court, corrections and 3D.

## Impact

New `src/vball/camera_motion.py` and tests; `vball.court_registration` (smoothing, gap filling, corrections);
pipeline decode, court and trajectory stages (version bumps; the four 4K videos and the five clips rerun);
`docs/results/court-keypoints.md` and `docs/results/trajectory.md`. No new data or training.
