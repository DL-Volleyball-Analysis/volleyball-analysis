## ADDED Requirements

### Requirement: Rally path up to now
The boards and the rendered analysis video SHALL draw the rally's 3D path from its start to the current time, older
parts fading, low-quality parts dashed, and SHALL keep the ball marker visible for every frame of the rally that has
a path position; only a break in the path hides the marker, and the break is drawn as a gap.

#### Scenario: Between two flights
- **WHEN** playback is at a frame between two joined flights of a rally
- **THEN** the ball marker is on the path and the arc drawn so far stays visible

### Requirement: Touch markers
The boards and the rendered video SHALL mark each touch on the path with the player's shirt number or track id and
the role (serve, receive, dig, set, attack, block), uncertain roles marked as such.

#### Scenario: Attack
- **WHEN** playback passes the attack touch of a rally
- **THEN** a marker at that touch shows the attacker and "attack"
