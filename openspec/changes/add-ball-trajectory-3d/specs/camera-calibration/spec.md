# Spec Delta

## Purpose

Recovers the camera (focal length and pose) for each shot from the court keypoints, so image points can be turned into rays in court coordinates.

## ADDED Requirements

### Requirement: Calibration per shot
For each shot with enough keypoints, including at least one net-band point off the floor plane, the system SHALL estimate the focal length and the camera pose in the court frame, and SHALL report the median reprojection error of the keypoints in pixels.

#### Scenario: Broadcast shot
- **WHEN** a shot shows the court corners and the net band
- **THEN** its calibration has a focal length, a camera position above the floor, and a reprojection error

#### Scenario: Floor points only
- **WHEN** a shot shows only floor keypoints
- **THEN** the calibration assumes square pixels and a centred principal point, and is marked as constrained by the floor only

### Requirement: Calibration quality gate
A calibration whose reprojection error exceeds the configured threshold SHALL be marked unusable, and no 3D trajectory SHALL be computed from it.

#### Scenario: Bad keypoints
- **WHEN** a shot's keypoints are inconsistent and the error is above the threshold
- **THEN** the shot's flights are reported as not reconstructed, with the reason
