# Spec Delta

## ADDED Requirements

### Requirement: Player-only detector
The installed player detector SHALL be trained on labelled volleyball sequences in which only the players on
court are labelled, and a newly trained detector SHALL replace the current one only if it scores higher IDF1 and
higher precision on the SportsMOT volleyball validation sequences.

#### Scenario: Adopting a fine-tuned detector
- **WHEN** a fine-tuned detector reaches higher IDF1 and precision than the installed one on the validation sequences
- **THEN** it is installed, and the comparison (model, settings, metrics) is recorded in docs/results/player-tracking.md

#### Scenario: A worse detector
- **WHEN** a fine-tuned detector does not beat the installed one on both metrics
- **THEN** the installed detector stays and the result is recorded

### Requirement: At most twelve players
After filtering, the system SHALL keep at most 12 players per frame, preferring people placed on court and then
higher detection confidence.

#### Scenario: Crowd at the side of the court
- **WHEN** 15 people remain in a frame after filtering
- **THEN** 12 are kept as players: first those placed on court, then the most confident

### Requirement: Role check without a court
The system SHALL assign each track a team by appearance (two teams) and SHALL mark tracks that match neither team
as role `other`; a track marked `other` that the court mapping places on the court SHALL stay a player. Tracks of
role `other` SHALL be excluded from court positions, actions and statistics but SHALL remain in the players table.

#### Scenario: Referee without a court
- **WHEN** the court is not found and the first referee, dressed unlike both teams, is tracked
- **THEN** the referee's track has role other and does not appear on the court map

#### Scenario: Libero
- **WHEN** the libero, dressed unlike the rest of the team, stands on the court in a shot with a usable court
- **THEN** the libero stays a player
