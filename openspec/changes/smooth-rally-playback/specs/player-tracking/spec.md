## ADDED Requirements

### Requirement: Stable tracks through short occlusions
On still cameras the players stage SHALL detect at the configured higher rate (default 15 Hz), and a track that
starts within the configured time and court distance of where a lost track of the same team ended SHALL take over the
lost track's id, so that a player hidden briefly behind the net or another player keeps one id.

#### Scenario: Player hidden for half a second
- **WHEN** a player is hidden behind a teammate for 0.5 s and reappears 0.4 m from where they were lost
- **THEN** the player keeps the same track id

#### Scenario: Different player appears
- **WHEN** a lost track ended 4 m from where a new track starts
- **THEN** the new track keeps its own id
