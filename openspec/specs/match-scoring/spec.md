# match-scoring Specification

## Purpose

Turns rally outcomes into the running match score and lets the user correct rally winners.

## Requirements

### Requirement: Indoor scoring rules
The running score SHALL follow indoor rules: a set is won at 25 points (15 in the deciding fifth set) with a lead of at least 2, and the match is best of five.

#### Scenario: Deuce
- **WHEN** team A leads 25-24
- **THEN** the set continues, and it ends when A leads 26-24

#### Scenario: Deciding set
- **WHEN** sets are 2-2 and team A reaches 15-13
- **THEN** team A wins the set and the match is 3-2

### Requirement: Score after every rally
Each rally SHALL carry the score after it: set number, both teams' points in that set, sets won, and whether the rally ended the set. A rally with no winner yet SHALL leave the score unchanged.

#### Scenario: Undecided rally
- **WHEN** a rally's winner is unknown
- **THEN** its score equals the previous rally's score

### Requirement: Manual winner correction
The user SHALL be able to set or clear a rally's winner; a correction SHALL take precedence over the model's winner, be stored separately from it, and every later score SHALL be recomputed.

#### Scenario: Correcting a rally
- **WHEN** the model said team B won rally 3 and the user sets team A
- **THEN** rally 3 shows A as the effective winner, the model's B is still stored, and scores from rally 3 on are recomputed

#### Scenario: Clearing a correction
- **WHEN** the user clears the correction on rally 3
- **THEN** the model's winner applies again
