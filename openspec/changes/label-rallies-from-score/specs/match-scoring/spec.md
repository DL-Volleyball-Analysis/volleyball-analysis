## ADDED Requirements

### Requirement: Point labels from the on-screen score
For matches with a known score bug, the system SHALL read the score once per second and SHALL report point changes
(time and scoring team) only for readings that move the score forward by one point or start a new set; other
readings SHALL be dropped as misreads.

#### Scenario: A point is scored
- **WHEN** the score bug changes from "(1) 06-04 (0)" to "(1) 07-04 (0)" and stays
- **THEN** a point change for team a is reported at the time of the change

#### Scenario: A misread
- **WHEN** one reading says "(1) 08-04 (0)" between two readings of "(1) 06-04 (0)"
- **THEN** no point change is reported
