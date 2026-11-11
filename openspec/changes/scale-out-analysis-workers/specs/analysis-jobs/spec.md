## MODIFIED Requirements

### Requirement: Recovery after interruption
A worker SHALL hold a lease on the job it runs and renew it while working; a running job whose lease has expired
SHALL be claimable again, and a job claimed more than the configured number of times SHALL fail with the reason.
Starting a worker SHALL NOT change jobs held by other workers.

#### Scenario: Worker restarted mid-job
- **WHEN** the only worker process is killed during a job and started again
- **THEN** that job is taken again once its lease has expired and processed

#### Scenario: Worker killed mid-job
- **WHEN** a worker process is killed during a job while another worker is running
- **THEN** after the lease expires the other worker takes the job and finishes it

#### Scenario: Second worker starts
- **WHEN** a second worker starts while the first is running a job
- **THEN** the first worker's job stays running with its lease and is not queued again

#### Scenario: A job that keeps killing workers
- **WHEN** a job's lease has expired more than the configured number of times
- **THEN** the job fails with a reason naming how many workers it lost

## ADDED Requirements

### Requirement: Several workers
The system SHALL support several worker processes on one database, each claiming jobs atomically, so that every
queued job is run by exactly one worker at a time.

#### Scenario: Concurrent claims
- **WHEN** four processes claim jobs at the same time from 100 queued jobs
- **THEN** each job is claimed exactly once

### Requirement: Clean stop
A worker that receives SIGTERM or SIGINT SHALL return its current job to the queue before exiting.

#### Scenario: Ctrl-C during a job
- **WHEN** the user stops a worker with Ctrl-C during a job
- **THEN** the job is queued again immediately, not after the lease expires

### Requirement: Stage timings
Each job SHALL record the wall time of every stage it ran, and the job endpoint SHALL return them.

#### Scenario: Finished job
- **WHEN** a job that ran from the trajectory stage finishes
- **THEN** its record lists the time of trajectory, events and rallies and no time for the stages it reused
