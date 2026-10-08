# Proposal

## Why

Coaches rate attackers by attack efficiency and servers by aces and errors, and the system cannot produce
either: nothing ties an attack or a serve to a player or to the point's outcome. Implements phase 1 of
[docs/prd/player-stats.md](../../../docs/prd/player-stats.md): fast coach tagging with outcomes and
statistics computed by the system.

## What Changes

- Team rosters per video (player numbers, optional names).
- Action tags at a video time: attack or serve, team, player number, outcome (kill / error / in play,
  ace / error / in play). Tags are stored apart from model output and keyed by time, so they survive
  re-analysis that changes rally boundaries.
- Outcome of the last tagged action of a rally inferred from the rally's effective winner unless set.
- Statistics per player and per team, match and per set: attempts, kills, errors, attack efficiency,
  kill rate; serves, aces, serve errors; incomplete when a rally has no winner.
- Match page: a tagging shortcut (tag key, number, Enter), a tag lane on the timeline, a statistics tab,
  CSV export.

Out of scope: automatic tag suggestions from action recognition, player tracking or 3D trajectories
(phase 2, a later change); reception / dig / set ratings; rotations and zones.

## Capabilities

### New Capabilities
- `player-stats`: rosters, action tags with outcomes, per-player and per-team statistics and export.

### Modified Capabilities
None. Rally winners and corrections (`match-scoring`) are read, not changed.

## Impact

- `src/vball`: new `stats` module (pure functions: outcome inference and statistics), unit-tested.
- Web app backend: `rosters` and `tags` tables; `GET/PUT /videos/{id}/roster`,
  `GET/POST /videos/{id}/tags`, `PATCH/DELETE /videos/{id}/tags/{tag_id}`, `GET /videos/{id}/stats`
  (JSON and CSV).
- Web app frontend: tagging shortcut, tag lane, statistics tab, roster editor; regenerated API types.
