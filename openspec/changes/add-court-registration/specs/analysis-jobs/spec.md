# Spec Delta

## ADDED Requirements

### Requirement: Recompute after court correction
When the user sets or clears a court correction, the system SHALL queue an analysis of that video starting at the first stage that uses court results (events), unless a job for the video is already queued or running, in which case that job SHALL pick up the correction when it reaches a stage that uses court results.

#### Scenario: Correction on an analysed video
- **WHEN** the user corrects a shot of a fully analysed video
- **THEN** a job starting at the events stage is queued, and the decode, court and ball results are reused
