# Spec Delta

## MODIFIED Requirements

### Requirement: Ordered analysis stages
The system SHALL analyse a video in the fixed stage order decode, court, ball, players, events, rallies, and SHALL record each stage's status as done, todo (not implemented), unavailable (missing model) or pending (not run yet).

#### Scenario: Court model missing
- **WHEN** a video is analysed and no court keypoint model is installed
- **THEN** the court stage is recorded as unavailable with a message saying the model is not trained yet, and later stages still run

#### Scenario: Players before events
- **WHEN** a video is analysed from the decode stage
- **THEN** the players stage runs after ball and before events, so events can use player positions
