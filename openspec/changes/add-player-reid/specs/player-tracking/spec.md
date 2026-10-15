## ADDED Requirements

### Requirement: Identity across gaps
The system SHALL be able to join two tracks that never coexist into one player identity when their appearance is
close, the movement between them is physically plausible, they are on the same side and team and their shirt numbers
do not conflict, and SHALL never produce more than twelve concurrent on-court identities.

#### Scenario: Player leaves the frame and returns
- **WHEN** a player's track ends at the frame edge and a new track of the same player starts two seconds later
- **THEN** both tracks carry one identity

#### Scenario: Teammates with the same shirt
- **WHEN** two teammates in the same shirt have close appearance but different shirt numbers
- **THEN** their tracks are not joined

### Requirement: Measured re-identification
The tracking evaluation SHALL report IDF1, HOTA, MOTA, identity switches and time per frame with and without each
re-identification step on the SportsMOT volleyball validation sequences, and a step SHALL be used by the pipeline only
when it raises IDF1 without lowering HOTA.

#### Scenario: A step that does not help
- **WHEN** appearance matching lowers HOTA on the validation sequences
- **THEN** the pipeline does not use it and the result is still recorded
