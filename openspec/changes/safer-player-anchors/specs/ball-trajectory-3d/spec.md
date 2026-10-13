## MODIFIED Requirements

### Requirement: Player-anchored touches
When player court positions are known at a flight's first or last frame, the fit SHALL include a prior that pulls
the ball's horizontal position there toward the nearest player within the configured radius, only when that player is
nearer to the ball's ray than any other player by at least the configured margin (otherwise that end is not anchored),
and each flight SHALL report which of its ends were anchored and to which position.

#### Scenario: Short attack
- **WHEN** a synthetic attack of under 0.5 s is reconstructed with the attacker's and the receiver's court positions known
- **THEN** its median 3D error is at most half the error of the same fit without anchors

#### Scenario: No players known
- **WHEN** no player positions are available for a flight
- **THEN** the flight is fitted without anchors and reports none

#### Scenario: Several players near the ray
- **WHEN** a synthetic attack is reconstructed with twelve players on court and the toucher's position off by up to 1 m
- **THEN** with the default margin its median 3D error is not worse than the same fit without anchors
