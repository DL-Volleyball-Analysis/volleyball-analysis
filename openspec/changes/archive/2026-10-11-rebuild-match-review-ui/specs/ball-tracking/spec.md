# Spec Delta

## ADDED Requirements

### Requirement: Detection coverage summary
The system SHALL report, for a tracked video, the fraction of frames with a ball detection in each of N equal time bins over the whole video (N chosen by the client, bounded), so a client can show where tracking found the ball without loading every frame.

#### Scenario: Coverage for a timeline
- **WHEN** a client asks for 100 bins of a 10-minute video whose ball was detected in the first half only
- **THEN** it receives 100 values, about 1 in the first 50 bins and 0 in the last 50

#### Scenario: Not tracked yet
- **WHEN** coverage is requested before ball tracking has run
- **THEN** the request fails with not found
