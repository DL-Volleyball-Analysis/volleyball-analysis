# PRD: Match review interface (web app)

Parent: [README.md](README.md) · OpenSpec: `openspec/changes/rebuild-match-review-ui/` · Current-state analysis: [`docs/webapp_redesign.md`](../webapp_redesign.md)

## Problem
The capstone interface is "upload → wait → watch an overlay video". Score, rallies and landings are invisible, playback re-renders ~60 times per second, and the build tool (Create React App) is unmaintained.

## User stories
1. As a coach, I drag a video in and analysis starts; the list shows which stage it is at and how far along.
2. As a coach, opening a match shows the score first; clicking any rally jumps the video to the start of that point.
3. As a coach, the court map shows where each point landed, with in and out drawn differently.
4. As a coach, I review a whole set with the keyboard: `J`/`K` previous/next rally, Space play/pause, `1`/`2` set the winner.
5. As a coach, rallies the system is unsure about are flagged, so I know what to check.
6. As a user, demo data is always labelled "demo", so I never mistake it for analysis results.
7. As a researcher, I can see each analysis stage's status (done, model not ready, not implemented yet).

## Requirements
**Library**
- Upload by drag-and-drop or file picker; analysis starts automatically.
- Each video shows name, duration, live analysis progress (stage + percentage) and score summary.
- A failed analysis shows its reason and a "Analyse again" action.

**Match page**
- Scoreboard: current set, points in this set, sets won; follows the playback position.
- Video with overlays: ball trail (last 0.5 s), court lines (when a court mapping exists); each layer switchable.
- Rally list: winner, reason, confidence; current rally highlighted; low confidence flagged.
- Rally timeline: the whole match as rally blocks; click to jump.
- Court map: 18 × 9 m to scale with landing points; current rally highlighted.
- Stage panel: every stage's status and message.

**General**
- Desktop and phone (phone: stacked layout with tabs).
- Fully keyboard-operable with visible focus; respects reduced motion; light and dark themes.
- Team colours consistent across scoreboard, timeline and map; never colour alone.

## Acceptance criteria
- Every user story passes on the 5 evaluation clips (demo rallies).
- No full-page re-render during playback: ≤ 5 UI commits per second measured with the React Profiler (overlays drawn directly on canvas).
- Any point reachable from the library in ≤ 2 clicks.
- Lighthouse accessibility ≥ 90.

## Out of scope
- Accounts, share links, cloud deployment (README §7 Q1).
- Clip or CSV export (after M5).
- Player statistics page (pending the player feature review).

## Technical choice (details in the OpenSpec design)
React + Vite + TypeScript: the most mature ecosystem and common in research tooling; the backend is FastAPI, so Next.js's server features are not needed.
