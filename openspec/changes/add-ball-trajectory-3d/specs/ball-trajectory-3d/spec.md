# Spec Delta

## Purpose

Places the ball in court metres during each free flight between touches, with values coaches use (landing, net-crossing height, release speed, apex) and the error of every estimate.

## ADDED Requirements

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

#### Scenario: Flight toward the camera
- **WHEN** a flight moves mostly along the camera's line of sight
- **THEN** it is marked low quality with the reason "depth poorly constrained"
