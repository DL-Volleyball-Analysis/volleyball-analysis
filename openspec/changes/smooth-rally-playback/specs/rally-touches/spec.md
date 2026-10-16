## ADDED Requirements

### Requirement: Touches with team, player and role
For every touch of a rally (a joint between two flights of the rally path, or the start of its first flight) the
system SHALL report the frame, the 3D or court position, the team (side of the net at the touch), the player (the
anchored player, else the nearest placed player of that team within the configured radius, else none), a role and a
confidence.

#### Scenario: Touch with a nearby player
- **WHEN** a touch lies 0.6 m from a placed player of the near team and every other player is more than 2 m away
- **THEN** the touch reports the near team and that player's track id

#### Scenario: No player nearby
- **WHEN** no placed player is within the configured radius of a touch
- **THEN** the touch reports its team and role with no player

### Requirement: Roles from the sequence of play
The first touch of a rally SHALL be the serve; after the ball crosses the net the receiving team's touches SHALL be
numbered from 1: receive (after a serve) or dig, then set, then attack.

#### Scenario: Serve, receive, set, attack
- **WHEN** a rally path has a first touch behind the far end line, then three touches on the near side, then a
  crossing to the far side
- **THEN** the roles are serve, receive, set, attack

#### Scenario: More than three touches
- **WHEN** a team has four counted touches before the ball crosses the net
- **THEN** the fourth touch is marked uncertain and the first three keep their roles

### Requirement: Blocks
A touch at the net within the configured time after the opponent's attack, by the defending team, SHALL be a block and
SHALL NOT advance that team's touch count.

#### Scenario: Block then dig
- **WHEN** the near team attacks, a far-team touch occurs at the net 0.2 s later, and the far team touches again
  2 m behind the net
- **THEN** the net touch is a block and the next touch is a dig numbered 1

### Requirement: Classifier as support only
Where the action classifier reports an action for the touching player at the touch, the touch confidence SHALL rise
when it agrees with the role and fall when it disagrees; the classifier SHALL NOT change the role.

#### Scenario: Disagreement
- **WHEN** the sequence gives "set" and the classifier reports "spike" for that player at the touch
- **THEN** the role stays "set" with lower confidence

### Requirement: Measured touch roles
The project SHALL report role accuracy and player accuracy on touches labelled by the owner (frame, player, role) on
amateur clips not used for tuning, and SHALL record the result in `docs/results/rally-playback.md`.

#### Scenario: Running the evaluation
- **WHEN** the touch evaluation runs on the labelled rallies
- **THEN** it prints role accuracy, player accuracy (touches with the player on camera) and the confusion of roles
