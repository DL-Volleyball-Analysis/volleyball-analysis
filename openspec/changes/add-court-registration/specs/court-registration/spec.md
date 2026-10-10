# Spec Delta

## Purpose

Maps image pixels to court metres for every frame of an analysed video so landings and in/out calls can be computed in court coordinates.

## ADDED Requirements

### Requirement: Court mapping for every frame
For each camera shot the system SHALL provide an image-to-court mapping that can be evaluated at any frame of the shot, in the court frame of `vball.court` (metres, x along the 18 m length, net at x = 9).

#### Scenario: Static camera
- **WHEN** a shot is filmed from a tripod
- **THEN** every frame in the shot maps the four court corners to within the shot's reported error of their true image positions

#### Scenario: Panning broadcast camera
- **WHEN** the camera pans within a shot
- **THEN** the mapping changes over the shot so that it follows the court rather than staying fixed to the first frame

### Requirement: Shot quality status
Each shot SHALL have a status of ok, needs_review or failed together with a numeric error estimate, and a shot whose mapping could not be estimated SHALL be marked failed rather than given a guessed mapping.

#### Scenario: Court hidden
- **WHEN** a shot shows only the crowd
- **THEN** the shot is marked failed and has no mapping

#### Scenario: Unreliable fit
- **WHEN** the detected keypoints of a shot fit a court only with a large error
- **THEN** the shot is marked needs_review and its error estimate is reported

#### Scenario: Floor and net disagree
- **WHEN** the floor keypoints fit a court with a small error but the detected net points are far from where a camera calibrated on those floor points places the net
- **THEN** the shot is marked needs_review with that distance reported

#### Scenario: Later stages and unreliable shots
- **WHEN** a shot is marked needs_review or failed
- **THEN** stages that use the court (player positions, 3D flights, landings) treat it as having no mapping, and the mapping stays available for review

### Requirement: Model per shot
When more than one court model is installed, the system SHALL register every shot with each model and keep, per
shot, the registration with the best status (ok, then needs review, then failed), breaking ties by the lower
floor-net consistency distance and then the lower fit error, and SHALL record which model each shot used.

#### Scenario: Broadcast and gym models
- **WHEN** a video's first shot is registered ok only by model A and its second shot only by model B
- **THEN** the first shot uses model A's registration, the second model B's, and each shot names its model

#### Scenario: One model installed
- **WHEN** only one court model is installed
- **THEN** every shot uses it, as before

### Requirement: Geometric sanity
The system SHALL reject a fitted mapping whose projected court is not a convex quadrilateral inside a plausible image area, and treat that frame as having no estimate.

#### Scenario: Mirrored fit
- **WHEN** a fit would place the court mirrored or folded
- **THEN** that fit is discarded

### Requirement: User court correction
The user SHALL be able to set a shot's court by giving the image positions of the four court corners at one frame; the correction SHALL apply to the whole shot, take precedence over the model, be stored separately from model output, and remain after any rerun. Clearing it SHALL restore the model result.

#### Scenario: Correcting a shot
- **WHEN** the user places the four corners on a frame of shot 2
- **THEN** shot 2 uses the corrected mapping with status ok and is marked as corrected

#### Scenario: Rerun keeps the correction
- **WHEN** the analysis is rerun from the decode stage
- **THEN** shot 2 still uses the user's correction

### Requirement: Measured accuracy
The project SHALL provide an evaluation that reports, on the held-out k6y7r test split and the external VNL split, the median and 90th-percentile error in metres of labelled court keypoints mapped through the predicted mapping.

#### Scenario: Running the evaluation
- **WHEN** the evaluation is run with a trained model
- **THEN** it prints both splits' median and p90 errors in metres and the number of images where no mapping was found
