# Verify notes (2026-10-08)

Walkthrough of every user story in `docs/prd/match-review.md`, on the 5 evaluation clips with demo
rallies, in Chrome (desktop 1280 px via a scaled iframe, phone 360 px, light and dark).

| # | Story | Result | Evidence |
|---|---|---|---|
| 1 | Drag a video in; list shows stage and progress | Pass | Uploaded `broadcast_side_high_men.mp4` through the page: row showed "Tracking the ball 25%", then "No rallies yet", no reload. Gap: progress sits at 25% for the whole ball stage (upstream tracker reports no progress); noted for a later change |
| 2 | Score first; any rally reachable from the library in ≤ 2 clicks | Pass | Score in the editor's title bar; library → match (1) → rally row or timeline block (2) seeks to the rally start (Playwright: Enter on rally 3 → 4.41 s) |
| 3 | Court map shows landings, in and out drawn differently | Pass | Landings tab: dot = in, × = out, team letter beside; same marks in the timeline's Landings lane |
| 4 | Keyboard review: J / K, Space, 1 / 2 / 0 | Pass | Playwright with trusted keys: K → 0.2 s, K → 2.31 s, J → 0.2 s, Space plays; unit tests for 1 / 2 / 0 and the inspector update |
| 5 | Low-confidence rallies flagged | Pass | ▲ in the rally table, inspector ("check this rally") and the timeline's Review lane; corrected rallies are no longer flagged |
| 6 | Demo data always labelled | Pass | Bordered "Demo data." notice above the editor; "(demo data)" in the library |
| 7 | Stage status visible | Pass | Analysis tab: "Not available yet — The court model has not been trained yet." etc. |

Acceptance criteria from the PRD:
- Playback commits: 50 in 10 s of playback on the 14 s clip, three runs (budget ≤ 50; exactly the 5 Hz design rate). An 8.4 s clip on loop gave 51 because the loop restart is a seek.
- Lighthouse accessibility: 100 on both pages after the revision-2 layout.
- Keyboard-only: every control reachable with a 2 px accent focus ring; no animation under reduced motion.
- 360 px: no horizontal overflow on either page in either theme.

Found and fixed during verification: page scrolling on every seek, J/K stuck when a rally starts off
the 200 ms grid, focus ring lost under reduced motion, a stray ring in the corner before the video
size is known, wrapped scores and clipped reasons on phones, overlapping ruler labels, rally rows
with unreadable accessible names, developer wording in stage messages.
