# Review experience v2: a web app a coach can use without us

Version 1.0 · 2026-10-12 · Owner: YuJia Liang · Parent: [match-review.md](match-review.md)

## Why
A walkthrough of the app on all nine analysed videos (2026-10-12, screenshots in the change folder) found:

| Where | Problem | Effect |
|---|---|---|
| Library | Upload is a thin dashed bar above the list | Users ask "where do I upload my own video?" |
| Library | Rows show raw file names in monospace, no thumbnail, no analysis state | You cannot tell which match is which, or whether analysis is running, done or stuck |
| Library | "No rallies yet" for both "not analysed" and "analysed, no rally found" | Ambiguous |
| Match | Why 2D / 3D is missing is hidden in the Analysis tab | Users think the system failed silently ("why no 3D for some videos?") |
| Match | A court that needs confirmation does not invite the user to set it | The fix (the court picker) exists but nobody finds it |
| Match | Court and player overlays are off by default; the video takes half the width; the right panel is mostly empty | The results are not visible at first sight |
| Match | Action and tag lanes print overlapping text ("Blk Spk Blk", "?") | Unreadable on any clip longer than a minute |
| Match | Score "A 0-0 B" shown when there are no rallies; a demo-data banner mentions "milestone M3" | Developer language, meaningless numbers |
| Everywhere | System font, grey on grey, no identity; the favicon looked like a basketball (fixed 2026-10-12) | Looks unfinished |

## Users and jobs
- **Coach / analyst (primary):** upload a match, see what the system found, fix what it got wrong (court, winners, tags),
  and get rally lists, player stats and the landing map.
- **Player:** watch their own actions.
- **Interviewer / reviewer:** understand in one minute what the system does and how reliable each part is.

## What
1. **Upload is the first thing you see**: an "Add match video" button in the header on every page, and a large drop
   area as the first card in the library; upload progress per file; an empty library explains what happens after upload.
2. **Library as match cards**: thumbnail, display name (editable; the file name stays as a detail), duration, upload
   date, analysis state (queued / analysing with stage and progress / needs you / done / failed) and the result summary
   (score from detected rallies, or "rallies could not be told on this footage").
3. **Analysis health on the match page**: one panel that lists what was found and what was not, each with the reason
   and the action that fixes it, e.g. "Court: needs your confirmation in 1 of 1 shot -> Set court"; "3D flights:
   unavailable until the court is set". Answers "why no 2D / 3D" in the product.
4. **Video first**: the video takes about two thirds of the width; overlays (ball, players, numbers, court) are on by
   default when the result exists, as a row of toggle chips on the video.
5. **Readable timeline**: lanes collapse to density strips (actions coloured by type) with labels only when zoomed in;
   zoom and pan; the rally lane and the playhead stay readable on a 90-minute match.
6. **Language**: no developer terms (milestone, stage version, demo data); the score appears only with rallies.
7. **Visual identity**: a type pair and colour palette chosen for an analysis tool (light default, dark theme kept),
   a consistent icon set, and the volleyball favicon.
8. **Delete and rename a match** from the library (with confirmation).

## Success
- First-time users find upload and the court fix without help (5 of 5 in a hallway test with classmates).
- Every missing result on the match page states why and what fixes it.
- Lighthouse accessibility stays 100; frontend coverage gate stays 85%; keyboard shortcuts keep working.
- Timeline stays readable (no overlapping text) on the 3-minute fixed-camera clips and a 90-minute match.

## Out of scope
Accounts and sharing; mobile editing (mobile stays view-only); new analysis features.
