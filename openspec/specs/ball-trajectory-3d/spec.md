# ball-trajectory-3d Specification

## Purpose

Places the ball in court metres during each free flight between touches, with values coaches use (landing, net-crossing height, release speed, apex) and the error of every estimate.

## Requirements

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
the ball's horizontal position there toward the nearest player within the configured radius, only when that player is
nearer to the ball's ray than any other player by at least the configured margin (otherwise that end is not anchored),
and each flight SHALL report which of its ends were anchored and to which position.

#### Scenario: Short attack
- **WHEN** a synthetic attack of under 0.5 s is reconstructed with the attacker's and the receiver's court positions known
- **THEN** its median 3D error is at most half the error of the same fit without anchors

#### Scenario: No players known
- **WHEN** no player positions are available for a flight
- **THEN** the flight is fitted without anchors and reports none

#### Scenario: Several players near the ray
- **WHEN** a synthetic attack is reconstructed with twelve players on court and the toucher's position off by up to 1 m
- **THEN** with the default margin its median 3D error is not worse than the same fit without anchors

### Requirement: Measured on realistic errors
The project SHALL report 3D error on synthetic rallies with missed, false and noisy detections at rates measured on
the evaluation clips, as an ablation (no constraints, bounds, + robust, + anchors), and SHALL report per real clip
how many segmented flights were kept and with what fit residual.

#### Scenario: Running the evaluation
- **WHEN** the trajectory evaluation runs
- **THEN** it prints the ablation table per flight type and the real-clip summary

### Requirement: Flights between touches
The system SHALL split the ball track into flights at points where the image velocity changes abruptly, and each flight SHALL have a start and end frame.

#### Scenario: Serve and receive
- **WHEN** a serve is received by a player
- **THEN** the serve and the pass after it are separate flights

### Requirement: Ballistic 3D reconstruction
For each flight in a shot with a usable calibration, the system SHALL estimate a 3D path in the court frame that follows ballistic motion under gravity and best reprojects onto the 2D detections, SHALL give 3D positions for every frame of the flight including frames without a detection, and SHALL report the fit error in pixels.

#### Scenario: Synthetic arc
- **WHEN** an arc rendered through a known camera with 2 px detection noise is reconstructed
- **THEN** the median 3D position error is at most 0.10 m

#### Scenario: Occluded frames
- **WHEN** the ball is hidden for 5 frames in the middle of a flight
- **THEN** those frames have 3D positions from the fitted path, marked as not observed

### Requirement: Derived flight values
Each reconstructed flight SHALL report, where they apply: the landing point where the path meets the floor, the height at which it crosses the net plane, the speed at its start, and its apex height.

#### Scenario: Ball crossing the net
- **WHEN** a flight crosses the plane x = 9 m
- **THEN** the crossing height and the crossing position along the net are reported

### Requirement: Honest uncertainty
A flight whose fit error exceeds the configured threshold, or which is too short to constrain depth, SHALL be marked low quality, and its derived values SHALL carry that flag.

#### Scenario: Impossible flight
- **WHEN** a fitted flight starts faster than any volleyball is hit (40 m/s) or its path leaves the hall
- **THEN** it is not reported as a flight, and the stage reports how many flights were left out and why

#### Scenario: Flight toward the camera
- **WHEN** a flight moves mostly along the camera's line of sight
- **THEN** it is marked low quality with the reason "depth poorly constrained"
