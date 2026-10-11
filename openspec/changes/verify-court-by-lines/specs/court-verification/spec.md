## ADDED Requirements

### Requirement: Line support
For a court mapping and a frame, the system SHALL compute line support: the share of evenly spaced points on the
projected court lines (inside the image) that lie within a few pixels of a thin bright line in the frame.

#### Scenario: Correct mapping
- **WHEN** the mapping of a broadcast frame puts the projected lines on the painted lines
- **THEN** line support is above the acceptance threshold

#### Scenario: Wrong mapping
- **WHEN** the mapping follows lines of another sport on a multi-sport gym floor
- **THEN** line support is below the acceptance threshold

### Requirement: Refinement
The system SHALL refine a keypoint-based mapping by searching nearby homographies for higher line support, and SHALL
keep the refined mapping only if its support is higher and its floor keypoint error stays within the fit limit.

#### Scenario: Slightly off mapping
- **WHEN** a mapping is offset by a few pixels from the painted lines
- **THEN** the refined mapping has higher line support and lower error on labelled points

### Requirement: Status from line evidence
A camera shot SHALL be ok when its median line support reaches the threshold and its floor fit error is within the
limit; otherwise it SHALL need review. The threshold SHALL be chosen on labelled training images, not on test images.

#### Scenario: Back view with net points at the posts
- **WHEN** a back view's floor mapping is correct and its net points sit at the net ends
- **THEN** the shot is ok
