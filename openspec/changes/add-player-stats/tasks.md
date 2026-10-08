# Tasks

## 1. `vball.stats`

- [ ] 1.1 Implement outcome inference (user outcome first, last tag from the effective winner, earlier tags in play, unknown without a winner) and verify unit tests for every spec scenario
- [ ] 1.2 Implement statistics per player / team / set with empty ratios and the incomplete count, and verify against a hand-calculated fixture match
- [ ] 1.3 Implement CSV rows (player x set, player match, team totals) and verify the two-set export scenario

## 2. Backend (web app)

- [ ] 2.1 Add `rosters` and `tags` tables and the roster endpoints with the duplicate-number rule; verify API tests
- [ ] 2.2 Add the tag endpoints (create adds unknown numbers to the roster; patch; delete) and joining tags to rallies by time with the 2 s nearest-rally rule; verify API tests, including re-analysis that moves rally boundaries
- [ ] 2.3 Add `GET /videos/{id}/stats` (JSON and CSV) and verify that a winner correction changes the returned outcome and statistics; regenerate frontend types

## 3. Frontend (web app)

- [ ] 3.1 Tagging shortcut (T / S, team 1 / 2, number, Enter, Esc) at the playhead; verify keyboard tests, including the three-key common case
- [ ] 3.2 Tag lane on the timeline and tag editing in the inspector (outcome override, delete); verify component tests
- [ ] 3.3 Statistics tab with set filter, incomplete marks and CSV export; verify component tests against the fixture
- [ ] 3.4 Roster editor; verify the duplicate-number message
- [ ] 3.5 Verify by screenshot in both themes and at phone width

## 4. Docs

- [ ] 4.1 Update the web app README (shortcuts, statistics), the PRD index and README status; validate with `openspec validate add-player-stats --strict`
