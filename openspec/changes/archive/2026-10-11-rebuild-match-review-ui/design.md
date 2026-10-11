# Design

## Context

- The API is already rewritten (`openspec/specs/video-library`, `analysis-jobs`, `match-scoring`): videos, job SSE stream, stages, ball window, rallies with scores and corrections. FastAPI publishes the schema at `/openapi.json`.
- The capstone frontend has been removed from branch `redesign`; a bare Vite + React + TypeScript scaffold exists in `frontend/`.
- Court mappings arrive later via `add-court-registration`; the UI must work without them.
- Rally data is demo-only until milestone M3.

## Goals / Non-Goals

**Goals:**
- A small, layered frontend where server state, playback time and drawing are separate concerns.
- Types that cannot drift from the API.

**Non-Goals:**
- Server-side rendering, routing on the server, auth.
- A component library or design system package; a handful of components is enough.

## Decisions

### Stack
React 19 + Vite + TypeScript (strict). TanStack Query for server state, React Router for the two pages, Tailwind CSS v4 for styling, Vitest for unit tests.
*Alternatives:* Next.js — its server features duplicate FastAPI and would make every video/canvas component a client component; Vue — would discard React experience with no gain for this app. See PRD "Technical choice".

### Types generated from OpenAPI
`openapi-typescript` generates `src/api/schema.d.ts` from the running backend's `/openapi.json` (`npm run gen:api`). Components use named aliases from `src/api/types.ts`; no hand-written response types. CI fails if the generated file is stale (`gen:api` + `git diff --exit-code`) when the backend is reachable; otherwise the committed file is used.

### Directory layout
```
frontend/src/
  api/        client.ts (fetch + errors), schema.d.ts (generated), types.ts, queries.ts (hooks), jobStream.ts (SSE)
  playback/   clock.ts (time store), useRallyAt.ts
  court/      geometry.ts (court lines in metres, in/out), CourtMap.tsx
  match/      MatchPage.tsx, Scoreboard.tsx, RallyList.tsx, RallyTimeline.tsx, VideoStage.tsx,
              OverlayCanvas.tsx, StagePanel.tsx, LayerMenu.tsx, useReviewShortcuts.ts
  library/    LibraryPage.tsx, UploadDrop.tsx, VideoRow.tsx
  ui/         small shared pieces (Badge, Notice, Tabs)
  theme.css   tokens (colour, type, spacing) for light and dark
```
Folders follow features, not file kinds, so a change to the court map touches `court/` only.

### Playback time lives outside React state
`playback/clock.ts` is a tiny external store holding the `<video>` element. Two read paths:
- `OverlayCanvas` reads `video.currentTime` directly inside `requestAnimationFrame` and draws; it never sets React state.
- Components that need the time (scoreboard, highlighted rally) subscribe through `useSyncExternalStore` to a value quantised to 200 ms, so they re-render at most 5 times per second (spec "Smooth playback").
This replaces the capstone's 60 Hz `setCurrentTime`.

### Overlay alignment
The canvas sits over the video with the same box; on each frame it computes the `object-fit: contain` letterbox from `videoWidth/videoHeight` and the element size, and scales image-pixel coordinates into it. Device pixel ratio is applied for sharp lines. Court lines are drawn from `vball` court geometry (metres) through the shot's mapping once the court API exists; until then the layer is disabled with a tooltip.

### Ball data loading
Fetch ball positions in windows of 30 s around the playhead (`/ball?start&end`), cached by TanStack Query keyed by window index; prefetch the next window. Avoids loading a full match track at once.

### Live job progress via SSE
`jobStream.ts` opens one `EventSource` per running video and writes each event into the query cache (`['video', id]` and the list). It closes on done/failed and invalidates stages and rallies so the page refreshes once. No polling.

### Corrections are optimistic
Pressing 1/2/0 sends `PATCH /rallies/{idx}`; the cache is updated optimistically and replaced with the server's recomputed list on success, rolled back on error with a notice.

### Visual design: analyst tool, light by default
Decided with the owner on 2026-10-08 after the first pass (dark slate cards, pill badges, giant coloured numerals) read as generated. Reference feel: Hudl, Linear — a working tool where the video is the hero and everything else is quiet.

- **Structure from rules, not cards.** Sections are separated by whitespace and 1 px hairlines; no card backgrounds, no shadows, radius ≤ 4 px. Lists are tables with a header row (rally list: #, winner, end, time, confidence).
- **One accent.** Blue `#1F5BD8` for focus, selection, progress and links only. Team colours are restrained and used only where a team is shown: A teal `#0F766E`, B crimson `#9F1239`, always next to the team letter.
- **Neutrals.** Page `#FFFFFF`, subtle panel/header fill `#F6F7F9`, hairline `#E3E6EA`, text `#15171A`, secondary text `#5B636E`. Dark theme counterparts exist but are opt-in.
- **Type.** Public Sans (self-hosted via `@fontsource`), one family: 400 text, 500 labels, 600 headings and score; tabular figures for every number. Scale 13 / 14 / 16 / 20 / 28 px. No condensed display face, no oversized coloured digits: the score is 28 px ink with team letters.
- **Marks, not badges.** Needs review = ▲ in the review colour with the text "Review" for screen readers; corrected = "edited" in secondary text; demo data = a one-line bordered notice, plain text in the library. No filled pills.
- **Court map as line art.** White court, ink lines at 1 px, light grey free zone; landings: filled dot = in, × = out, in the winner's team colour with the team letter beside it.
- **Theme.** Light by default; a Light/Dark switch in the header persists per viewer (`localStorage`, wrapped in try/catch, falls back to light).
- `src/theme.test.ts` keeps enforcing WCAG AA for both themes.

### Visual design, revision 2: after soredemo-web (approved by the owner 2026-10-08)
The owner pointed to `~/Documents/Soredemo/soredemo-web` as the reference. What it does well is a
discipline, not a skin, so we borrow the discipline and leave its brand behind.

**Borrowed**
- **The product is shown as the product's own shape.** Soredemo's page is a Mac desktop because the
  app lives in the menu bar. Our product is a video review tool, so the match page becomes an
  *editor*: video top-left, an inspector on the right, and a multi-lane timeline across the bottom.
- **Lanes, one hue per kind.** Like Soredemo's Video / Audio / Zoom / Captions lanes, the timeline has
  lanes for Rallies (A above, B below), Ball (detected frames as ticks), Landings and Review (▲).
  Lane colours share one saturation and lightness and differ in hue; team colours stay A / B.
- **Inspector rows** instead of sections: the selected rally's winner, end, confidence, landing and
  correction as label / value rows in 12-13 px, the way an editor shows properties.
- **System font stack, nothing downloaded** (`-apple-system`, SF Pro, Helvetica Neue, Arial). Large
  display headings are tight-tracked; UI text is small and quiet.
- **Mono means machine-origin.** Monospace only for strings the system produced: timecodes,
  file names, stage ids, model names, video ids. Everything else is the sans.
- **Contrast is documented on every token** (text floor 4.5:1; a "mute" colour for marks only,
  never text), and enforced by `src/theme.test.ts` as now.
- **Surfaces:** a light grey page (`#f4f4f5`) with white, 10 px-radius windows and one soft shadow for
  the editor; rules inside. Theme stays **light by default**, dark only when the viewer picks it
  (owner's decision 2026-10-08; Soredemo follows the system instead).
- **Honest captions:** anything drawn rather than real is captioned as a drawing; demo rallies keep
  their notice.
- **Tokens only in one file; no raw colours in components.**

**Not borrowed (Soredemo's brand, not a design principle)**
Mac menu bar and notch, traffic-light window buttons, desk objects and stickers, kaomoji, aqua
gloss buttons, Apple artwork, the dotted cutting-mat background.

**Changes against revision 1:** font (Public Sans → system stack), surfaces (no cards → one editor
window on a grey page), timeline (single strip → lanes), right column (stacked sections → inspector +
tabs for Rallies / Landings / Analysis). Theme default unchanged (light).

**Ball lane data:** the whole-match ball lane needs detection coverage for the full video, which
the 30 s ball windows cannot give cheaply, so the API adds `GET /videos/{id}/ball/coverage?bins=N`
(fraction of frames with a detection per bin; delta in `specs/ball-tracking`).

### Score summary on the API
`main.py` computes the summary from the last rally with the existing `running_score` (no new storage) and returns it on `Video`. The summary is part of the delta in `specs/video-library`.

## Risks / Trade-offs

- [Generated types drift if the backend is not running in CI] → Commit `schema.d.ts`; the check runs only when the backend can start in CI (it needs `vball`), otherwise a warning.
- [Demo rallies make the UI look finished] → Demo notice is a spec requirement; demo flag shown in the library too.
- [Court overlay untestable until M1] → Layer present but disabled; tasks for it live in `add-court-registration` follow-up.
- [Tailwind utility soup hurts maintainability] → Tokens in `theme.css`; components keep class lists short and extract repeated patterns into `ui/`.

## Migration Plan

The old frontend is gone from `redesign`; `main` still has it. No data migration. The dev setup becomes `npm run dev` with a Vite proxy from `/api` to `localhost:8000`.
