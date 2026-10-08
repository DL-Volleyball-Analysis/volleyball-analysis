# analysis-jobs Specification

## Purpose

Runs video analysis as an ordered, resumable pipeline of stages outside the request path, and reports its progress.

## Requirements

### Requirement: Ordered analysis stages
The system SHALL analyse a video in the fixed stage order decode, court, ball, events, rallies, and SHALL record each stage's status as done, todo (not implemented), unavailable (missing model) or pending (not run yet).

#### Scenario: Court model missing
- **WHEN** a video is analysed and no court keypoint model is installed
- **THEN** the court stage is recorded as unavailable with a message saying the model is not trained yet, and later stages still run

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
