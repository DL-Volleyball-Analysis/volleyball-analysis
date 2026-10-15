## ADDED Requirements

### Requirement: Correcting predictions into labels
The review app SHALL let the user label sampled frames of an analysed video for court points, ball, players, actions
and rally winner, starting from the pipeline's prediction, and SHALL store a prediction as a label only when the user
explicitly accepts or edits it.

#### Scenario: Accepting a court
- **WHEN** the user opens a frame whose predicted court is right and presses accept
- **THEN** the 14 court points are stored as a court label for that frame

#### Scenario: Frame not reviewed
- **WHEN** the user leaves a frame without accepting or editing a task
- **THEN** no label is stored for that task

### Requirement: Partial, versioned labels
A label SHALL belong to one video, frame and task, record its author and time, and never be overwritten; a newer
version SHALL supersede it, and a frame MAY carry labels for any subset of tasks.

#### Scenario: Correcting a label later
- **WHEN** the user moves a ball label that was saved yesterday
- **THEN** both versions are kept and the export uses the newer one

### Requirement: Dataset export split by video
The project SHALL export the labels together with the converted public datasets in one format, assigning whole videos
to train, validation or test, with the test videos fixed once chosen.

#### Scenario: Two frames of one video
- **WHEN** a video has labelled frames
- **THEN** all its frames are in the same split
