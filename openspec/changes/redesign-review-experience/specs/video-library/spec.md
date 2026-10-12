## ADDED Requirements

### Requirement: Display names
Each video SHALL have a display name, initially derived from the file name (extension removed, separators replaced by
spaces), which the user can change; the file name SHALL stay available as a detail.

#### Scenario: Rename
- **WHEN** the user renames fixed_hawaii_pennstate to "Hawaii vs Penn State, set 2"
- **THEN** the library card and match page show the new name and the file name is unchanged

### Requirement: Thumbnails
The system SHALL store a thumbnail per video, taken from a frame 10% into the video, when the video is added.

#### Scenario: New upload
- **WHEN** a video is uploaded
- **THEN** its library card shows a frame of the match
