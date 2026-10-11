# Spec Delta

## MODIFIED Requirements

### Requirement: Ordered analysis stages
The system SHALL analyse a video in the fixed stage order decode, court, ball, players, actions, trajectory, events, rallies, and SHALL record each stage's status as done, todo (not implemented), unavailable (missing model) or pending (not run yet).

#### Scenario: Court model missing
- **WHEN** a video is analysed and no court keypoint model is installed
- **THEN** the court stage is recorded as unavailable with a message saying the model is not trained yet, and later stages still run

#### Scenario: Actions after players
- **WHEN** a video is analysed from the decode stage
- **THEN** the actions stage runs after players, so action detections can be assigned to player tracks

#### Scenario: Action models missing
- **WHEN** the action or number model is not installed
- **THEN** the actions stage is recorded as unavailable, and later stages still run
