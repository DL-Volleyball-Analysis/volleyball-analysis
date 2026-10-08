# ball-tracking Specification

## Purpose

Locates the ball in every frame of a video so later stages (landing, rallies, overlays) can use its image trajectory.

## Requirements

### Requirement: Per-frame ball output
The system SHALL produce exactly one record per decoded frame containing the frame index, a visibility flag and the ball's image coordinates in pixels of the original video.

#### Scenario: Ball detected
- **WHEN** the model finds the ball in frame 120
- **THEN** the record for frame 120 has visible = 1 and x, y in original-resolution pixels

#### Scenario: Ball not detected
- **WHEN** the model does not find the ball in a frame
- **THEN** that frame's record has visible = 0 and x, y are missing values, never 0 or a guessed position

### Requirement: Replaceable tracking model
The system SHALL let the tracking model be chosen by name (default VballNet V4c) without changing the output format.

#### Scenario: Switching models
- **WHEN** ball tracking is run with model "fast_v1" instead of "v4c"
- **THEN** the output has the same columns and one record per frame

### Requirement: Honest tracking metrics
The system SHALL report label-free proxy metrics (detection rate, jump count) separately from labelled accuracy (precision, recall, F1), and SHALL NOT compute accuracy without labelled frames.

#### Scenario: No labels available
- **WHEN** a clip has no labelled frames
- **THEN** only proxy metrics are reported for it and accuracy is reported as not measured
