# player-stats Specification

## Purpose

Attributes attacks and serves to players and turns them, with the point outcomes, into the statistics
coaches use: attack efficiency, kill rate, aces and serve errors.

## Requirements

### Requirement: Rosters
Each video SHALL have a roster per team, a list of unique player numbers with optional names, that the
user can edit.

#### Scenario: Duplicate number
- **WHEN** the user adds number 7 to team A, which already has a number 7
- **THEN** the change is rejected with a message, and the roster is unchanged

### Requirement: Action tags
The user SHALL be able to tag an attack or a serve at a video time with a team and a player number, and
to edit or delete a tag. Tags SHALL be stored apart from model output, keyed by video time, and SHALL be
kept when the video is analysed again.

#### Scenario: Tag survives re-analysis
- **WHEN** a video with tags is analysed again and its rally boundaries change
- **THEN** every tag is kept at its time and is counted in the rally that now contains that time

#### Scenario: Number not on the roster
- **WHEN** the user tags player 12 of team B and the roster has no 12
- **THEN** the tag is saved and the number is added to team B's roster

### Requirement: Tag outcomes
Each tag SHALL have an outcome: kill, error or in play for an attack; ace, error or in play for a serve.
An outcome set by the user SHALL take precedence. Otherwise the last tag of a rally SHALL take its outcome
from the rally's effective winner (the tagged team won: kill or ace; it lost: error), and earlier tags of
the rally SHALL be in play. When the rally has no effective winner, the last tag's outcome SHALL be unknown.

#### Scenario: Last attack of a won rally
- **WHEN** a rally's last tag is an attack by team A and team A won the rally
- **THEN** the attack's outcome is kill

#### Scenario: Winner corrected
- **WHEN** the user changes that rally's winner to team B
- **THEN** the attack's outcome becomes error and the statistics are recomputed

### Requirement: Statistics
For each player and each team, for the match and for each set, the system SHALL report attack attempts,
kills, errors, attack efficiency = (kills − errors) / decided attempts and kill rate = kills / decided
attempts, where decided attempts are the attempts whose outcome is known, and serves, aces and serve errors.
Ratios with no decided attempts SHALL be empty, not zero. Statistics that include a tag with an unknown
outcome SHALL be marked incomplete with the number of such tags.

#### Scenario: Efficiency
- **WHEN** a player has 10 attacks with 4 kills and 2 errors
- **THEN** attack efficiency is 0.200 and kill rate is 0.400

#### Scenario: Undecided rally
- **WHEN** a player's only attack is the last tag of a rally without a winner
- **THEN** the player's statistics show 1 attempt, empty ratios, and are marked incomplete (1 unknown)

#### Scenario: Unknown outcome does not count as a miss
- **WHEN** a player has 4 attacks: 1 kill, 2 errors and 1 with an unknown outcome
- **THEN** attack efficiency is (1 − 2) / 3 = −0.333, attempts show 4, and the line is marked incomplete

### Requirement: Statistics view and export
The match page SHALL show the statistics per player and per team with a set filter, and SHALL export them
as CSV with one row per player and set plus team totals.

#### Scenario: Export
- **WHEN** the user exports the statistics of a two-set match
- **THEN** the CSV has a row for every player in each set, a match row per player, and team total rows
