# Proposal

## Why

Coaches and the 3D-trajectory research both need the ball in metres, not pixels: where the serve went, how high the set was, where the ball crossed the net. A homography cannot place an airborne ball, so this needs a calibrated camera and a physical model of each flight. Implements [docs/prd/tactics-board.md](../../../docs/prd/tactics-board.md).

## What Changes

- Camera calibration per shot (focal length and pose) from the court keypoints including the net band.
- A `trajectory` pipeline stage: split the ball track into flights, fit a ballistic 3D path to each, derive landing point, net-crossing height, release speed and apex, each with a fit error.
- API for 3D flights per time window.
- Web app: a 2D tactics board (top-down ground tracks, heights, landings, players when available) and a rotatable 3D board, as tabs next to the video.

Depends on `add-court-registration` (mappings and keypoints) and should be archived after `add-player-tracking`, which modifies the same stage-order requirement.

Out of scope: spin, multi-camera fusion, real-time, touch classification (events stage).

## Capabilities

### New Capabilities
- `camera-calibration`: per-shot intrinsics and pose from court keypoints, with reprojection error.
- `ball-trajectory-3d`: ball flights in court metres with derived values and fit errors.
- `tactics-board`: 2D and 3D views of a rally's ball flights (and players) for the user.

### Modified Capabilities
- `analysis-jobs`: the stage order gains `trajectory` between `players` and `events`.

## Impact

- `src/vball`: new `calibration` and `trajectory` modules (numpy / OpenCV / SciPy least squares).
- Web app: `trajectory` stage, `GET /videos/{id}/flights?start=&end=`, tactics board components (SVG for 2D, three.js for 3D, a new frontend dependency).
