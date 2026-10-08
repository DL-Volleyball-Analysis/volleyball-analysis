# PRD: Ball trajectory on a tactics board (2D and 3D)

Parent: [README.md](README.md) · OpenSpec: `openspec/changes/add-ball-trajectory-3d/`

## Problem
The video shows the ball in image pixels. Coaches think in court terms: where the serve went, the direction of an attack, how high the set was. Researchers need the ball in metres to measure speed and height. Today only the image track exists.

**Why the 2D board also needs 3D:** a court homography is valid only for points on the floor. Mapping an airborne ball through it gives the point where the camera ray meets the floor, which is far from the ball's true ground position and moves the wrong way as the ball rises. The 2D board therefore shows the ground projection of a reconstructed 3D path, not the homography of the image track.

## User stories
- As a coach, I replay a rally on a top-down court: the ball's path, where it landed, and (with player tracking) where the players stood.
- As a coach, I rotate a 3D view of the rally to see set height and attack angle.
- As a coach, I read serve speed, set height and the height at which the ball crossed the net.
- As a researcher, I get per-frame 3D ball positions with an uncertainty, for single-camera 3D trajectory research.

## Requirements
1. **Camera calibration** per shot from the court keypoints, including the net band (non-coplanar points): focal length and camera pose, with a reprojection error.
2. **Flight segmentation:** split the ball track into flights between touches (sharp changes in image velocity, later confirmed by the events stage).
3. **3D reconstruction** of each flight: fit a ballistic path (gravity known, air drag optional) to the 2D detections by minimising reprojection error; fill frames where the ball was not detected; report per-flight fit error.
4. **Derived values:** landing point (path meets z = 0), net-crossing height, serve speed at release, apex height of sets.
5. **2D tactics board:** top-down court with each flight's ground track, height shown by colour or labels, landing marks; players from player tracking when available.
6. **3D tactics board:** a rotatable 3D court with the reconstructed path and the net.
7. **Honesty:** every 3D value carries its fit error; flights that fit badly are shown as such, not smoothed into plausible curves.

## Approach
Single-camera 3D is possible because a free-flying ball must follow a parabola: one camera gives the ray to the ball in every frame, and gravity fixes where along those rays the ball is. Known weak points: flights that are short, mostly towards or away from the camera, or interrupted by occlusion are poorly constrained.

## Acceptance criteria
- Synthetic test: arcs rendered through a known camera are reconstructed within 0.10 m (median) after adding 2 px detection noise.
- Calibration: reprojection error of the 14 keypoints ≤ 5 px median on the k6y7r test images.
- Real footage: net-crossing heights are above the net top for balls that crossed (sanity); landing points within 0.5 m of labelled landings (labels from M5).
- Fit error shown for every flight in the UI.

## Out of scope
- Spin, multi-camera fusion, real-time.

## Dependencies
- Court keypoints with net points (court model v2, training now), ball tracking, events (touches) for confirmed flight boundaries, player tracking for players on the board.

## Open questions
- Whether air drag is needed: decided by comparing fit errors with and without it on real flights (does not change requirements).
