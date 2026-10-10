# Spec Delta

## ADDED Requirements

### Requirement: Suggested tags
Spike and serve events SHALL be offered as suggested attack and serve tags with team (from the player's side of
the net) and number (from the track's vote) when known; a suggestion SHALL be shown as such, SHALL NOT count in
any statistic until the user accepts it, and the user SHALL be able to accept, edit or dismiss it.

#### Scenario: Accepting a suggestion
- **WHEN** the user accepts a suggested attack by team A number 10 at 12.4 s
- **THEN** a tag identical to one typed for team A number 10 at 12.4 s is created and the suggestion is gone

#### Scenario: Unknown number
- **WHEN** a spike event's track has no number
- **THEN** the suggestion asks for the number before it can be accepted
