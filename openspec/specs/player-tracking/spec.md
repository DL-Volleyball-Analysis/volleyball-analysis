# player-tracking Specification

## Purpose

Finds the players on court in an analysed video, keeps each one's identity through a rally and places them on the court, so positions and later statistics can be attributed.

## Requirements

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

### Requirement: Player-only detector
The installed player detector SHALL be trained on labelled volleyball sequences in which only the players on
court are labelled, and a newly trained detector SHALL replace the current one only if it scores higher IDF1 and
higher precision on the SportsMOT volleyball validation sequences.

#### Scenario: Adopting a fine-tuned detector
- **WHEN** a fine-tuned detector reaches higher IDF1 and precision than the installed one on the validation sequences
- **THEN** it is installed, and the comparison (model, settings, metrics) is recorded in docs/results/player-tracking.md

#### Scenario: A worse detector
- **WHEN** a fine-tuned detector does not beat the installed one on both metrics
- **THEN** the installed detector stays and the result is recorded

### Requirement: At most twelve players
After filtering, the system SHALL keep at most 12 players per frame, preferring people placed on court and then
higher detection confidence.

#### Scenario: Crowd at the side of the court
- **WHEN** 15 people remain in a frame after filtering
- **THEN** 12 are kept as players: first those placed on court, then the most confident

### Requirement: Role check without a court
The system SHALL assign each track a team by appearance (two teams) and SHALL mark tracks that match neither team
as role `other`; a track marked `other` that the court mapping places on the court SHALL stay a player. Tracks of
role `other` SHALL be excluded from court positions, actions and statistics but SHALL remain in the players table.

#### Scenario: Referee without a court
- **WHEN** the court is not found and the first referee, dressed unlike both teams, is tracked
- **THEN** the referee's track has role other and does not appear on the court map

#### Scenario: Libero
- **WHEN** the libero, dressed unlike the rest of the team, stands on the court in a shot with a usable court
- **THEN** the libero stays a player
