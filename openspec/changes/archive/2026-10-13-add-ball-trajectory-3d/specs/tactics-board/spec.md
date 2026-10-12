# Spec Delta

## Purpose

Shows a rally's ball flights (and players when known) on the court from above and in 3D, synchronised with the video.

## ADDED Requirements

### Requirement: 2D tactics board
The match page SHALL offer a top-down court that shows, for the selected rally, each flight's ground track from its 3D path (not the image track mapped through the floor homography), the height along it, the landing mark, and players' positions when player tracking is available.

#### Scenario: Attack to the back corner
- **WHEN** the selected rally ends with an attack landing in a back corner
- **THEN** the board shows the attack's ground track ending at that corner with its landing mark

### Requirement: 3D tactics board
The match page SHALL offer a rotatable 3D court with the net and the selected rally's 3D flights.

#### Scenario: Rotating the view
- **WHEN** the user drags on the 3D board
- **THEN** the view rotates around the court and the flights stay in place relative to the court

### Requirement: Synchronised with the video
Both boards SHALL mark the ball's position at the current playback time.

#### Scenario: Scrubbing
- **WHEN** the user drags the timeline playhead
- **THEN** the ball marker on the board moves along the flight to the same moment

### Requirement: Quality is visible
Low-quality flights SHALL be drawn distinctly (for example dashed) with their reason available, and frames not observed by the camera SHALL be distinguishable from observed ones.

#### Scenario: Low-quality flight
- **WHEN** a flight is marked low quality
- **THEN** it is drawn dashed and its reason shows on hover or focus
