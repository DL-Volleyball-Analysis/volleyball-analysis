## ADDED Requirements

### Requirement: One path per rally
Within a rally, consecutive flights SHALL be fitted jointly so that the end of one flight and the start of the next
are the same 3D point at the same time (the touch), and every frame between the first and last flight of the rally
SHALL have a 3D position from the fitted path.

#### Scenario: Synthetic rally with gaps
- **WHEN** a synthetic serve-receive-set-attack rally is rendered with 30% missed and 10% false detections
- **THEN** the joined path covers every frame from serve to landing with no break, and its median 3D error is not
  worse than fitting the flights separately

### Requirement: Breaks in the path
Where two flights cannot be joined (no detection near the touch for longer than the configured gap, or a joined fit
that breaks the bounds or exceeds the residual threshold), the path SHALL break there, each part SHALL be fitted
alone, and the break SHALL carry its reason.

#### Scenario: Unseen touch
- **WHEN** the ball leaves the image for 2 s between two flights
- **THEN** the path breaks between them with the reason "ball not seen for 2.0 s"

### Requirement: Path continuity measured
The project SHALL report per clip the share of rally time with a 3D ball position and the number of breaks per rally,
before and after joining.

#### Scenario: Personal clips
- **WHEN** the playback evaluation runs on the personal and fixed clips
- **THEN** it prints coverage and breaks per rally for each clip
