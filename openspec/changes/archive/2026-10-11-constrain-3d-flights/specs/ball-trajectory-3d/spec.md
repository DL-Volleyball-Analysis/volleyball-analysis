# Spec Delta

## ADDED Requirements

### Requirement: Robust flights
Before judging a flight's quality, the system SHALL drop detections whose reprojection residual exceeds the
configured outlier threshold, refit the flight on the rest, and report how many detections were dropped; a
flight left with fewer than the minimum detections SHALL not be reconstructed.

#### Scenario: False detections inside a flight
- **WHEN** a synthetic serve has 10% of its detections replaced by points elsewhere in the image
- **THEN** those points are dropped and the median 3D error is within 0.3 m

### Requirement: Bounded fit
The fitted path SHALL stay within the hall (the court plus the configured margin), above the floor, and below the
speed limit for the whole flight; a fit whose solution lies on a bound SHALL be marked low quality with the
reason.

#### Scenario: Solution in front of the camera
- **WHEN** an unconstrained fit of a track would place the ball a few metres from the camera
- **THEN** the bounded fit keeps the path inside the hall, or the flight is marked low quality, never drawn at the camera

### Requirement: Player-anchored touches
When player court positions are known at a flight's first or last frame, the fit SHALL include a prior that pulls
the ball's horizontal position there toward the nearest player within the configured radius, and each flight SHALL
report which of its ends were anchored.

#### Scenario: Short attack
- **WHEN** a synthetic attack of under 0.5 s is reconstructed with the attacker's and the receiver's court positions known
- **THEN** its median 3D error is at most half the error of the same fit without anchors

#### Scenario: No players known
- **WHEN** no player positions are available for a flight
- **THEN** the flight is fitted without anchors and reports none

### Requirement: Measured on realistic errors
The project SHALL report 3D error on synthetic rallies with missed, false and noisy detections at rates measured on
the evaluation clips, as an ablation (no constraints, bounds, + robust, + anchors), and SHALL report per real clip
how many segmented flights were kept and with what fit residual.

#### Scenario: Running the evaluation
- **WHEN** the trajectory evaluation runs
- **THEN** it prints the ablation table per flight type and the real-clip summary
