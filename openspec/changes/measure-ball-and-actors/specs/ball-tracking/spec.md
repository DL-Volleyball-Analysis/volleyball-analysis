# Spec Delta

## ADDED Requirements

### Requirement: Ball detection measured on labelled frames
The project SHALL report ball detection precision, recall and F1 against labelled frames of a public volleyball
dataset's official test split, at stated distance thresholds, for every ball method the pipeline can use.

#### Scenario: Running the ball evaluation
- **WHEN** the evaluation runs on the Volleyball dataset test split
- **THEN** it prints precision, recall and F1 at 4 and 10 pixels for each method, and the share of frames with a visible ball

### Requirement: Fixed objects are not the ball
The ball tracker SHALL drop a candidate whose image patch does not change against neighbouring frames once the
camera's own motion is removed, and SHALL link the remaining candidates over time with a limit on the ball's step.

#### Scenario: Floor dash under a panning camera
- **WHEN** the camera pans over a white floor dash that the detector reports as a ball while the ball flies elsewhere
- **THEN** the track follows the ball and never the dash
