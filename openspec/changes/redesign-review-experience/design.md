# Design

## Context
The current UI (change rebuild-match-review-ui, "revision 2") follows an editor layout with the system font, grey
surfaces and monospace file names. It works but hides state (analysis progress, why results are missing) and does not
scale to long videos (overlapping timeline labels). Constraints kept: React + Vite + Tailwind, TanStack Query, the
existing API, keyboard shortcuts, Lighthouse accessibility 100, coverage gate 85%, light default with a dark theme,
and the project rule "no AI-looking UI; analyst-tool style" (memory: ui-design-direction).

## Visual system
Subject: a coach's review desk for volleyball matches. The look borrows from the sport's own print and signage:
scoreboards (condensed numerals), the court's line work (thin, exact rules) and the ball's yellow and blue.

| Token | Light | Dark | Use |
|---|---|---|---|
| paper | #F5F7FA | #0E151D | page |
| surface | #FFFFFF | #15202B | cards, panels |
| ink | #14202C | #E7ECF2 | text |
| muted | #5A6876 | #93A1AF | secondary text |
| line | #DAE0E7 | #26333F | rules, borders |
| court | #1D4E9E | #6E9BE6 | primary actions, focus, selection |
| ball | #F2B705 | #F2B705 | ball trail, ball-related highlights |
| team-a / team-b | #0F7B6C / #B4234A | #34B3A0 / #E0587E | teams |
| attention | #B45309 | #F0A04B | "needs you" |

Type: **Barlow** (UI text, 14/20 base, 600 for headings) and **Barlow Condensed** (scores, timecodes, big numbers,
tabular). Self-hosted with @fontsource, nothing loaded from a CDN. Monospace only for file names in detail views.
Shape: 6 px radius on cards, 4 px on controls; one shadow level for floating menus only; cards separated by line, not
shadow. Icons: Lucide (one stroke width).

Rejected: cream + serif editorial look, dark-with-neon "sports app" look, SaaS card grid with gradients (all generic).

## Layout

Library
```
+------------------------------------------------------------------------------+
| (ball) Volleyball Analysis        Matches                 [+ Add match video] |
+------------------------------------------------------------------------------+
| Matches                                                    search  sort v     |
| +----------------+ +----------------+ +----------------+ +----------------+  |
| |   drop videos  | | [thumbnail]    | | [thumbnail]    | | [thumbnail]    |  |
| |   here or      | | Canada v Italy | | Hawaii v UCI   | | Women, side    |  |
| |  [Choose files]| | 2:30  Oct 11   | | 2:30  Oct 11   | | 0:05  Oct 7    |  |
| |                | | ! Set court    | | Analysing 62%  | | A 2-1 B        |  |
| +----------------+ +----------------+ +----------------+ +----------------+  |
+------------------------------------------------------------------------------+
```

Match
```
+------------------------------------------------------------------------------+
| < Matches   Canada vs Italy                         A 12 - 10 B  set 2   ... |
+--------------------------------------------------+---------------------------+
|                                                  | Health | Rallies | Players|
|                  video (2/3 width)               |  Stats | 3D board          |
|                                                  |---------------------------|
|                                                  | v Ball      71% of frames |
|  [Ball] [Players] [Numbers] [Court]   (chips)    | ! Court     needs you     |
|                                                  |   [Set court]             |
|                                                  | - 3D        needs court   |
+--------------------------------------------------+---------------------------+
| timeline: rallies | ball | actions (density) | tags | review      zoom - +   |
+------------------------------------------------------------------------------+
```

## Decisions
- **Health is computed by the backend** (`GET /videos/{id}/health`) from stage results, so the library card and the
  match page say the same thing and the wording is tested in one place.
- **Thumbnails at import** with OpenCV into `data/results/<id>/thumb.jpg`; served by `GET /videos/{id}/thumbnail`.
- **Display name** is a new nullable column; the API returns `display_name` (falls back to the derived name).
- **Timeline density**: events binned per pixel column; labels drawn only if the gap between neighbours exceeds the
  label width; zoom keeps the playhead in view.
- **Overlay defaults** from result availability, remembered per user in localStorage (try/catch, works without it).

## Risks
- Visual change breaks the screenshot-based figures in the papers: regenerate them after the change.
- More requests on the library (health per card): one batched endpoint `GET /videos?with=health`.
