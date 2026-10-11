# Spec Delta

## Purpose

Finds the players on court in an analysed video, keeps each one's identity through a rally and places them on the court, so positions and later statistics can be attributed.

## ADDED Requirements

### Requirement: Player detections and tracks
For each analysed frame the system SHALL output the detected players with an image box, a confidence and a track id, and a track id SHALL refer to the same person for as long as the tracker keeps that person.

#### Scenario: Player crosses another
- **WHEN** two players cross paths at the net and separate again
- **THEN** each keeps the track id they had before crossing, unless the tracker reports the track as lost

### Requirement: On-court filtering
When the court mapping of a frame exists, the system SHALL keep only people whose feet map inside the court plus a free-zone margin, and SHALL label every kept player with the side of the net they stand on.

#### Scenario: Referee on the stand
- **WHEN** the first referee stands beside the net post outside the free zone
- **THEN** the referee is not reported as a player

#### Scenario: No court mapping
- **WHEN** a frame has no court mapping
- **THEN** detections and tracks are still reported, and court position, side and on-court filtering are marked unavailable for that frame

### Requirement: Court positions
Each kept player SHALL have a court position in metres in the court frame of `vball.court`, taken from the midpoint of the bottom edge of the box mapped through the frame's court mapping.

#### Scenario: Player at the service line
- **WHEN** a player stands on the end line of side A
- **THEN** the reported position has x within the court's end-line tolerance of 0 m

### Requirement: Measured tracking accuracy
The project SHALL provide an evaluation that reports HOTA, IDF1, MOTA and detection recall and precision on labelled volleyball sequences, and SHALL NOT present unlabelled proxies (track counts, detection rates) as accuracy.

#### Scenario: Evaluating the baseline
- **WHEN** the evaluation runs on the SportsMOT volleyball validation sequences
- **THEN** it prints each metric per sequence and overall, the model and tracker used, and the frame rate the detector ran at
