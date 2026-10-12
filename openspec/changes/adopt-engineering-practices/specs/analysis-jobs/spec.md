## ADDED Requirements

### Requirement: Pipeline in the analysis package
The staged pipeline SHALL be part of the `vball` package (`vball.pipeline`) and be usable without the web app; the
web app, scripts and tests SHALL import it as a package, without editing `sys.path`.

#### Scenario: Script use
- **WHEN** a script runs analysis stages on a match
- **THEN** it imports `vball.pipeline` and the stages produce the same files the web app would

#### Scenario: Results unchanged by the move
- **WHEN** one fixed end-line clip and one broadcast clip are analysed before and after the move
- **THEN** every stage's JSON and CSV output is identical, ignoring timestamps

## MODIFIED Requirements

### Requirement: Ordered analysis stages
The system SHALL analyse a video in the fixed stage order decode, court, ball, players, actions, trajectory, events, rallies, and SHALL record each stage's status as done, todo (not implemented), unavailable (missing model) or pending (not run yet).

#### Scenario: Court model missing
- **WHEN** a video is analysed and no court keypoint model is installed, or its file differs from models/manifest.json
- **THEN** the court stage is recorded as unavailable with a message saying the model is missing or is not the expected version, and later stages still run

#### Scenario: Actions after players
- **WHEN** a video is analysed from the decode stage
- **THEN** the actions stage runs after players, so action detections can be assigned to player tracks

#### Scenario: Action models missing
- **WHEN** the action or number model is not installed
- **THEN** the actions stage is recorded as unavailable, and later stages still run

#### Scenario: Players before events
- **WHEN** a video is analysed from the decode stage
- **THEN** the players stage runs after ball and before events, so events can use player positions

#### Scenario: Trajectory before events
- **WHEN** a video is analysed from the decode stage
- **THEN** the trajectory stage runs after players and before events, so events can use 3D landing points
