# Design

## Context

- Rallies live in the `rallies` table with the model's winner and the user's `winner_override`; the API
  returns the effective winner and the running score (`vball.scoring`).
- Re-analysis replaces the rally rows, and rally boundaries can move.
- The match page has a playback clock (`playback/clock.ts`), a multi-lane timeline and keyboard review
  (`useReviewShortcuts`).

## Goals / Non-Goals

**Goals:** statistics a coach trusts (standard definitions, outcomes that follow winner corrections,
incomplete data shown as such); tagging fast enough to do while reviewing.
**Non-Goals:** automatic tagging, rally-quality ratings, rotations.

## Decisions

### Module ownership
| Responsibility | Module |
|---|---|
| Outcome inference, statistics, CSV rows (pure, no I/O) | new `vball.stats` |
| Rosters and tags storage | web app `database.py` (`rosters`, `tags` tables) |
| Endpoints, joining tags to rallies | web app `main.py` |
| Tagging shortcut, tag lane, statistics tab, roster editor | web app `src/stats/` |

### Tags keyed by time, not by rally
A tag stores the video time, kind (attack / serve), team, player number and an optional user outcome.
Its rally is found at read time: the rally whose [start, end] contains the time, else the nearest rally
within 2 s, else none (shown as "outside rallies" and excluded from statistics). Re-analysis therefore
never orphans or mis-assigns tags by index.
*Alternative:* a `rally_idx` foreign key. Rejected: indices shift when rallies are re-detected.

### Outcome inference in one pure function
`vball.stats.outcomes(tags, rallies)` returns each tag's effective outcome and whether it was inferred.
The same function serves the API and the tests, so the rules in the spec are tested once.

### Statistics shape
`vball.stats.summarise(tags_with_outcomes, rallies)` returns rows keyed by (team, player, set | "match"):
counts and ratios, plus `unknown` (tags with unknown outcome). Ratios are `None` without attempts. Team
totals are sums of the player counts, ratios recomputed from the sums (never averaged).

### Tagging interaction
`T` starts an attack tag and `S` a serve tag at the playhead (playback pauses) in a small entry field;
digits type the player number, `A` / `B` switch the team (letters, because digits are the number: `1` / `2`
cannot both pick a team and type number 12), `Enter` saves, `Esc` cancels. The team defaults to the team
last tagged. Tags show as marks on a "Tags" timeline lane; selecting one opens it in the inspector for
outcome override or delete. Three key presses for the common case: `T`, number, `Enter`.

### API
- `GET/PUT /videos/{id}/roster` — both teams' numbers and names.
- `GET/POST /videos/{id}/tags`, `PATCH/DELETE /videos/{id}/tags/{tag_id}`.
- `GET /videos/{id}/stats?format=json|csv` — computed on request from tags and current rallies (cheap).

## Risks / Trade-offs

- [Coaches tag only rally-ending attacks] → efficiency is biased upwards; the statistics tab shows the
  share of rallies with at least one tag, and the help text says that in-play attacks belong in the count.
- [Tag near a rally boundary] → nearest-rally rule with a 2 s limit; the inspector shows the rally a tag
  counts in.
- [Blocked attacks] → counted as attack errors (standard); a separate "blocked" count is a later addition.

## Migration Plan

New tables are created on start (`CREATE TABLE IF NOT EXISTS`); existing databases need no migration.

## Open Questions

- Whether coaches want serve receive ratings next; it does not change this change's specs.
