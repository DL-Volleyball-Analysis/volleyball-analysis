# Spec Delta

## ADDED Requirements

### Requirement: Recompute after court correction
When the user sets or clears a court correction, the system SHALL queue an analysis of that video starting at the first stage that uses court results (players), unless a job for the video is already queued or running, in which case no second job is created and that job SHALL apply the correction if it has not yet passed the court stage.

#### Scenario: Correction on an analysed video
- **WHEN** the user corrects a shot of a fully analysed video
- **THEN** a job starting at the players stage is queued, and the decode, court and ball results are reused
