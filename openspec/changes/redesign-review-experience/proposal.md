# Proposal

## Why

A walkthrough of the web app on all nine analysed videos (2026-10-12) showed that a first-time user cannot find the
upload, cannot tell which matches are analysed, does not learn why 2D / 3D results are missing or how to fix them, and
meets unreadable timeline lanes and developer wording. The look is unfinished. Implements
[docs/prd/review-experience.md](../../../docs/prd/review-experience.md).

## What Changes

- Header "Add match video" on every page; the library becomes a grid of match cards (thumbnail, display name,
  duration, date, analysis state, result) with a large drop card first; rename and delete with confirmation.
- Backend: a thumbnail per video, a display name, and an analysis "health" summary per video (what was found, what
  was not, why, and which user action fixes it).
- Match page: video about two thirds of the width with overlay chips on by default; an Analysis health panel replaces
  the stage list as the first inspector tab, with "Set court" actions; score only when rallies exist; no demo wording
  in developer terms.
- Timeline: density strips per lane, labels only when zoomed, zoom and pan.
- New visual system (type, palette, icons) replacing the grey system-font look; light default, dark kept.

## Capabilities

### Modified Capabilities
- `match-review-ui`: upload entry, library cards, analysis health, overlays on by default, readable timeline,
  wording, visual system.
- `video-library`: display names, thumbnails, rename.

## Impact

`webapp/frontend/src/**` (library, match, ui, theme), `webapp/backend/main.py` (thumbnail, rename, health endpoint),
`webapp/backend/database.py` (display name). No analysis changes. Tests and coverage gates stay.
