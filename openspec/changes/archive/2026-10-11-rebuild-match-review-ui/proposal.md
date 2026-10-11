# Proposal

## Why

The web app's frontend is still the capstone version: it is built around per-frame overlays, shows no score, rallies or landing map, re-renders the whole player about 60 times per second during playback, uses the unmaintained Create React App toolchain, and no longer matches the rewritten API. Coaches need a match page centred on the score and the rallies. Implements [docs/prd/match-review.md](../../../docs/prd/match-review.md) (milestone M2).

## What Changes

- **BREAKING** Replace the capstone frontend entirely (it has already been removed from branch `redesign`).
- Library page: upload by drag-and-drop or file picker, live analysis progress per video, failure reason with retry, score summary.
- Match page: scoreboard following the playback position, video with ball-trail and court-line overlays, rally list, rally timeline, scaled court map with landing points, stage status panel.
- Keyboard review: previous/next rally, play/pause, assign or clear a rally's winner.
- Demo rallies are always labelled as demo data.
- API: the video list includes each video's current score summary so the library does not fetch every video's rallies.

Out of scope: accounts and sharing, clip or CSV export, player statistics, the court-check (corner dragging) screen — that follows once `add-court-registration` provides the court API.

## Capabilities

### New Capabilities
- `match-review-ui`: what the user can see and do in the browser to follow analysis and review a match.

### Modified Capabilities
- `video-library`: listing videos also returns each video's score summary.
- `ball-tracking`: a detection coverage summary over the whole video, for the timeline's ball lane.

## Impact

- Web app `frontend/`: new React + Vite + TypeScript app (replaces the CRA app).
- Web app `backend/main.py`: score summary on video responses; no other API change.
- CI: frontend job builds the new app and runs its unit tests.
