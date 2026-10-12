# camera-motion Specification

## Purpose
TBD - created by archiving change follow-camera-motion. Update Purpose after archive.

## Requirements

### Requirement: Camera motion
The system SHALL estimate, for every frame of a video, the image-to-image homography from the previous frame, using
only the video, and SHALL give the mapping between any two frames of a camera shot.

#### Scenario: Still camera
- **WHEN** the camera does not move while players do
- **THEN** warping a frame by the estimated motion does not increase its difference to a later frame

#### Scenario: Panning camera
- **WHEN** the camera pans to follow play
- **THEN** warping a frame by the estimated motion lowers its difference to a frame one second later

### Requirement: Court follows the camera
Court smoothing SHALL warp neighbouring samples to a sample's frame before combining them, and sampled frames without
a detected court SHALL get the nearest detected court warped to them when it is at most 5 s away, marked as filled.

#### Scenario: Pan with missed detections
- **WHEN** the court model misses a few samples in the middle of a pan
- **THEN** those samples get a court that moves with the camera, marked as filled

### Requirement: Corrections follow the camera
A user's court correction SHALL be carried by the camera motion to every sampled frame of its shot.

#### Scenario: One correction on a panning shot
- **WHEN** the user corrects the court at one frame of a shot in which the camera pans
- **THEN** the court at a later frame has moved with the camera, not stayed where the user clicked

### Requirement: 3D per flight
Each 3D flight SHALL be calibrated and fitted in the image of one frame of that flight: the nearest court sample's
keypoints and the flight's ball positions are warped to it.

#### Scenario: Pan during a rally
- **WHEN** the camera pans between the court sample and the flight
- **THEN** the flight is reconstructed with the camera of its own frame
