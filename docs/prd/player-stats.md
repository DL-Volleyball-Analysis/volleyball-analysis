# PRD: Player statistics (attack efficiency and serve)

Parent: [README.md](README.md) · OpenSpec: `openspec/changes/add-player-stats/`

## Problem
Coaches judge attackers by efficiency, not by impressions: of all the attacks a player hit, how many
scored and how many were errors. The capstone recognised five actions frame by frame, but never tied an
action to a player or to the point's outcome, so it produced no statistics. Today the web app knows
rallies and (soon) who won each point, but not who attacked or served.

## User stories
- As a coach, after a match I see each player's attacks, kills, errors and attack efficiency, and each
  server's aces and errors, for the match and per set.
- As a coach, I record who attacked while reviewing, with a few key presses at the moment of the attack,
  and the outcome of the rally's last attack is filled in from the point winner.
- As a coach, I export the statistics to share with the team.
- As a researcher, the tags double as labelled data for an automatic attacker detector later.

## Definitions (standard indoor statistics)
| Statistic | Definition |
|---|---|
| Attack attempt | an attack hit at the opponent (spike, tip, roll shot) |
| Kill | attempt that wins the point directly |
| Attack error | attempt hit out or into the net, or blocked for a point |
| Attack efficiency | (kills − errors) / attempts |
| Kill rate | kills / attempts |
| Ace / serve error | serve that wins / loses the point directly |

## Requirements
1. Team rosters per match: player numbers and optional names for both teams.
2. Tag an attack or a serve at the playhead with team and player number; edit and delete tags.
3. Each tag has an outcome: kill / error / in play for attacks, ace / error / in play for serves. The last
   tagged action of a rally gets its outcome from the rally's effective winner unless the coach sets one.
4. Statistics per player and per team, for the match and per set, using the definitions above, recomputed
   whenever a tag, an outcome or a rally winner changes.
5. A statistics view in the match page and a CSV export.
6. Tags are stored apart from model output, like winner corrections, and survive re-analysis.
7. Statistics computed from rallies whose winner is unknown are marked incomplete, not silently counted.

## Approach
- **Phase 1 (this change):** coach tagging + automatic outcomes and statistics. No new model; usable as
  soon as rallies and winners exist (winners can be corrected by hand today).
- **Phase 2 (later change):** suggested tags. The capstone's action recogniser (YOLOv11m, validation
  mAP@0.5 0.945) proposes spikes and serves; player tracking and the 3D trajectory propose the attacker;
  the coach accepts or fixes. Needs the action model revived (README §7 Q2) and is measured against the
  phase 1 tags.

## Acceptance criteria
- Statistics match a hand calculation on a fixture match (unit tests cover every definition and the
  incomplete case).
- Tagging an attack takes at most 3 key presses (tag key, player number, Enter) without the mouse.
- Changing a rally winner updates the affected outcome and statistics without a page reload.

## Out of scope
- Reception, dig and set quality ratings; rotation and zone statistics (later, with player positions).
- Automatic tagging (phase 2).
- Player identity across matches.

## Dependencies
- Rallies and winners: rally-scoring (M3); manual winners work before M3.
- Match review interface (match-review).
