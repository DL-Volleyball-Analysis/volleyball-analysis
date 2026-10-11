# Spec Delta

## ADDED Requirements

### Requirement: Acting player weighted by the ball
When a ball position is known, the system SHALL weight each player's action score by how close the ball is to
that player, and SHALL report the effect on labelled per-player actions with parameters chosen on validation data.

#### Scenario: Two players look like setting
- **WHEN** two players get the same set score and the ball is at one of them
- **THEN** only the player at the ball is labelled as setting

#### Scenario: Ball unknown
- **WHEN** no ball position is known for a frame
- **THEN** the action scores of that frame are unchanged
