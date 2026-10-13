# analysis-jobs Specification

## Purpose

Runs video analysis as an ordered, resumable pipeline of stages outside the request path, and reports its progress.

## Requirements

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

### Requirement: Stage result reuse
The system SHALL recompute a requested start stage and every stage after it, and SHALL reuse an earlier stage's stored result when it exists and its version matches the current code.

#### Scenario: Rerun from ball tracking
- **WHEN** a rerun starts from the ball stage after a complete analysis
- **THEN** the decode and court results are reused and the ball, events and rallies stages are recomputed

#### Scenario: Stage version changed
- **WHEN** the stored decode result has an older version than the current code
- **THEN** decode and all later stages are recomputed even if the rerun starts later

### Requirement: Background jobs
The system SHALL run analysis in a worker separate from the API, and SHALL allow at most one queued or running job per video.

#### Scenario: Second request while running
- **WHEN** an analysis is requested for a video whose job is queued or running
- **THEN** the request is rejected with a conflict error and no new job is created

### Requirement: Job progress
Each job SHALL expose its status (queued, running, done, failed), current stage, overall progress from 0 to 1 and, when failed, an error message; clients SHALL be able to follow it as a live event stream that ends when the job finishes.

#### Scenario: Following a job
- **WHEN** a client subscribes to a running job's event stream
- **THEN** it receives an event whenever the job state changes and the stream closes after a done or failed event

### Requirement: Recovery after interruption
The system SHALL return jobs left running by a stopped worker to the queue when a worker starts.

#### Scenario: Worker restarted mid-job
- **WHEN** the worker process is killed during a job and started again
- **THEN** that job is queued again and processed

### Requirement: Work scales with the footage
Stages SHALL NOT repeat work that the footage does not need: shots with a still camera SHALL get court keypoint samples
at 1 per second and one camera calibration for all their flights, and the rallies stage SHALL check a few frames first
and report out-of-training footage without a full pass over the video.

#### Scenario: Fixed end-line camera
- **WHEN** a 3-minute clip from a still camera is analysed
- **THEN** the court, 3D and rallies stages together take at least 3x less time than before, with the same court
  status, calibrated shots and rallies result

#### Scenario: Moving broadcast camera
- **WHEN** the camera pans during a shot
- **THEN** its court samples stay at 5 per second and each flight gets the camera of its own frame

### Requirement: Recompute after court correction
When the user sets or clears a court correction, the system SHALL queue an analysis of that video starting at the first stage that uses court results (players), unless a job for the video is already queued or running, in which case no second job is created and that job SHALL apply the correction if it has not yet passed the court stage.

#### Scenario: Correction on an analysed video
- **WHEN** the user corrects a shot of a fully analysed video
- **THEN** a job starting at the players stage is queued, and the decode, court and ball results are reused

### Requirement: Pipeline in the analysis package
The staged pipeline SHALL be part of the `vball` package (`vball.pipeline`) and be usable without the web app; the
web app, scripts and tests SHALL import it as a package, without editing `sys.path`.

#### Scenario: Script use
- **WHEN** a script runs analysis stages on a match
- **THEN** it imports `vball.pipeline` and the stages produce the same files the web app would

#### Scenario: Results unchanged by the move
- **WHEN** one fixed end-line clip and one broadcast clip are analysed before and after the move
- **THEN** every stage's JSON and CSV output is identical, ignoring timestamps
