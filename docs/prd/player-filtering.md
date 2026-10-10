# PRD: Only the players on court

Parent: [README.md](README.md) · OpenSpec: `openspec/changes/filter-on-court-players/` · Research: [../research/directions.md](../research/directions.md)

## Problem
Player tracking boxes everyone the detector sees: referees, line judges, coaches, the bench and spectators. On
SportsMOT volleyball validation 39% of detections are people off court, which caps tracking at IDF1 0.484 and
precision 0.614 (an ideal on-court filter would reach 0.622). The current filter drops people outside the court
only when the court is found (2 of the 5 evaluation clips), and the first referee and line judges stand inside
its free-zone margin. Boxes on officials and spectators also clutter the video, the court map and, later, the
action events and statistics.

## User stories
- As a coach, I see boxes only on the twelve players, on the video and the court map.
- As a coach, the referee standing at the net is never counted as a player, even when the court is not found.
- As a researcher, the filter's effect is measured on labelled sequences, not judged by eye.

## Requirements
1. A detector trained to box players only: fine-tune on the SportsMOT volleyball training sequences, whose
   labels contain only the players on court. Trained on Kaggle; adopted only if it beats the current detector on
   SportsMOT volleyball validation (IDF1 and precision).
2. At most 12 players per frame: when more remain after filtering, keep the most confident (on-court ones first).
3. A role check that works without a court: group players into the two teams by appearance; tracks that match
   neither team are marked as other people (officials, staff). When the court is found and such a track stands on
   the court (the libero wears a different colour), it stays a player.
4. Other people are hidden from the court map, actions and statistics but stay inspectable (not deleted).

## Acceptance criteria
- SportsMOT volleyball validation: IDF1 and precision above the baseline (0.484 / 0.614), recorded with the
  model and settings in `docs/results/player-tracking.md`.
- On the five evaluation clips, no box on the first referee or line judges in the rendered videos (by eye), and
  every player on court still boxed.

## Out of scope
- Re-identification across camera cuts; jersey-based identity (change `add-player-actions`).

## Dependencies
- `add-player-tracking` (evaluation script, stage); `add-court-registration` (on-court filter).
- SportsMOT training sequences (CC BY-NC 4.0, research use, not redistributed: a private Kaggle dataset).
