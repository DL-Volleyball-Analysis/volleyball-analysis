# Proposal

## Why

Player tracking boxes referees, line judges, coaches and spectators: 39% of detections on SportsMOT volleyball
validation are people off court, capping IDF1 at 0.484 (precision 0.614; an ideal filter reaches 0.622). The
on-court filter only works when the court is found, and officials stand inside its margin. Implements
[docs/prd/player-filtering.md](../../../docs/prd/player-filtering.md).

## What Changes

- Fine-tune the player detector on SportsMOT volleyball training sequences (players-only labels) on Kaggle;
  adopt it only if it beats the baseline on validation.
- Keep at most 12 players per frame.
- `vball.teams`: group tracks into the two teams by appearance; tracks matching neither are marked `other`
  (kept on court when the court says they stand on it, e.g. the libero).
- Players table gains `role` (`player` / `other`) and `team` columns; the court map, actions and statistics use
  players only; the overlay shows others dimmed.

## Capabilities

### New Capabilities

### Modified Capabilities
- `player-tracking`: player-only detection, a 12-player cap and a role check that works without a court
  (added as new requirements; this change is archived after `add-player-tracking`).

## Impact

- `notebooks/train_player_detector.ipynb` (Kaggle), `scripts/build_sportsmot_detection.py`.
- `src/vball/players.py` (cap, role columns), new `src/vball/teams.py`.
- Web app: players stage version, overlay styling of `other`, render.py.
