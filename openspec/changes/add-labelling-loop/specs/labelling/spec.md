## ADDED Requirements

### Requirement: Pre-annotations from the pipeline
The project SHALL export an analysed video's pipeline output as CVAT pre-annotations (players as tracks with ids, the
14 court keypoints, the ball as a per-frame point or outside, actions as attributes), marked as model predictions.

#### Scenario: Ball not detected
- **WHEN** the pipeline has no ball in a frame
- **THEN** the ball point is marked outside in that frame

### Requirement: Only human-touched labels
The import SHALL keep an item as a label only when the labeller edited or explicitly accepted it, and SHALL drop items
still marked as model predictions.

#### Scenario: Untouched prediction
- **WHEN** a player box imported as a prediction was never edited or accepted
- **THEN** it is not in the dataset

### Requirement: Verified converters and split by video
The converters SHALL reproduce labelled ground truth exactly through a round trip (a tracking score of 1.0 on
SportsMOT ground truth), and the dataset SHALL assign whole videos to train, validation or test.

#### Scenario: Round trip
- **WHEN** SportsMOT ground truth is exported to CVAT format and imported back
- **THEN** evaluating it against the original gives HOTA 1.0

#### Scenario: Two frames of one video
- **WHEN** a video has labelled frames
- **THEN** all its frames are in the same split
