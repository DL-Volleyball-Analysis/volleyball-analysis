# Spec Delta

## ADDED Requirements

### Requirement: Score summary in the video list
Each video returned by the list and detail endpoints SHALL include a score summary taken from its last rally: sets won by each team, the current set number and both teams' points in it, the number of rallies, how many are corrected, and whether any rally is demo data; a video without rallies SHALL have no summary.

#### Scenario: Analysed video
- **WHEN** a video's last rally leaves sets at 1-0 and the second set at 12-10
- **THEN** its list entry shows sets 1-0, set 2, points 12-10

#### Scenario: No rallies yet
- **WHEN** a video has not been analysed
- **THEN** its list entry has no score summary
