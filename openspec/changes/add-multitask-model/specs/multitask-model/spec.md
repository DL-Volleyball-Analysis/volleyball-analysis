## ADDED Requirements

### Requirement: Learning from partially labelled data
The multi-task model SHALL train on samples labelled for any subset of its tasks, computing the loss only for the
tasks a sample is labelled for.

#### Scenario: A court-only image
- **WHEN** a training image has court keypoints but no player boxes or ball
- **THEN** only the court head's loss is computed for it

### Requirement: Adoption per head
The pipeline SHALL use a head of the multi-task model for a task only when it is at least as accurate as the current
single-task model on that task's held-out test and on the held-out amateur test videos, and SHALL otherwise keep the
single-task model.

#### Scenario: Ball head loses to WASB
- **WHEN** the ball head's F1 at 10 px on the gym test is below the single-task ball model's
- **THEN** the pipeline keeps the single-task ball model and records the result
