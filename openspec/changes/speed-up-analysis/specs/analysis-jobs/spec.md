## ADDED Requirements

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
