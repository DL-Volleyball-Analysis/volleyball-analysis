## ADDED Requirements

### Requirement: Court from painted lines
For a camera shot with a still camera, the system SHALL fit the court model to the painted lines of the shot's
background plate (the median of frames spread over the shot), considering bright and dark lines, and SHALL reject
fits that are implausible, smaller than 8% of the image, or shaped like a fan or a sliver.

#### Scenario: End-line camera
- **WHEN** a fixed camera behind an end line films a match on a court with white lines
- **THEN** the fitted court lies on the painted end, attack and centre lines and sidelines

#### Scenario: Dark volleyball lines on a multi-sport floor
- **WHEN** the volleyball lines are painted darker than the floor and other sports' lines are white
- **THEN** the fit follows the volleyball lines

### Requirement: Best evidence wins
For a still shot the system SHALL score the line fit and the keypoint fit on the same plate by line support and SHALL
use the higher-scoring one for every frame of the shot, recording which source it came from.

#### Scenario: Keypoints squeeze the court
- **WHEN** the keypoint fit puts the whole court into the near half of an end-line view
- **THEN** the line fit scores higher and is used

### Requirement: Status from line evidence
A still shot SHALL be ok when its chosen fit has at least five well supported court lines and at least 70% of its line
samples supported; otherwise it SHALL need review. The net check SHALL NOT decide the status of such shots.

#### Scenario: Wrong court with consistent net points
- **WHEN** a fit squeezes the court into the near half but its net points agree with it
- **THEN** the shot needs review unless the line evidence supports it
