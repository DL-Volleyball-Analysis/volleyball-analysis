# Tasks

## 1. Scaffold and tooling

- [x] 1.1 Configure the Vite app (TypeScript strict, `/api` proxy to `localhost:8000`, Tailwind v4, `@fontsource` Barlow / Barlow Condensed, Vitest) and verify `npm run build` and `npm test` succeed on an empty app
- [x] 1.2 Add `npm run gen:api` (openapi-typescript from the backend's `/openapi.json`), commit `src/api/schema.d.ts`, and verify a type error appears when a component reads a field the API does not have
- [x] 1.3 Add `theme.css` tokens for light and dark themes and verify both themes render the token sample page with WCAG AA contrast for text

## 2. API layer

- [x] 2.1 Add the score summary to `Video` in `backend/main.py` and verify backend tests for analysed, unanalysed and demo videos (delta `video-library`)
- [x] 2.2 Implement `api/client.ts` and `api/queries.ts` (videos, video, stages, rallies, ball windows, upload, start job, correct rally) and verify unit tests for error mapping and query keys
- [x] 2.3 Implement `api/jobStream.ts` (SSE into the query cache, close on finish, invalidate stages/rallies) and verify a unit test with a mocked EventSource

## 3. Library page

- [x] 3.1 Build `UploadDrop` (drag-and-drop and picker, per-file rejection message) and verify a test that a .txt file shows the rejection and does not call the API
- [x] 3.2 Build `VideoRow` with live stage and percentage, failure reason with retry, score summary with demo label, and verify component tests for queued, running, failed and done states
- [x] 3.3 Verify by running the backend + worker + demo import that uploads appear and progress updates live without reload

## 4. Playback core

- [x] 4.1 Implement `playback/clock.ts` with the 200 ms quantised subscription and verify unit tests that subscribers are not notified more than 5 times per simulated second
- [x] 4.2 Implement `useRallyAt` (current or last finished rally for a time) and verify unit tests for gaps between rallies, before the first and after the last rally
- [x] 4.3 Implement `VideoStage` + `OverlayCanvas` (letterbox mapping, DPR, 0.5 s ball trail from windowed ball data) and verify a unit test of the letterbox mapping and by eye that the trail sits on the ball after a resize

## 5. Match page

- [x] 5.1 Build `Scoreboard` bound to `useRallyAt` and verify a test that seeking into rally 20 shows the score after rally 20
- [x] 5.2 Build `RallyList` and `RallyTimeline` (highlight, low-confidence and corrected marks, select to seek) and verify component tests for each mark and that selecting seeks to the rally start
- [x] 5.3 Build `CourtMap` (to-scale court, in = circle, out = cross, team letters, current highlight) with `court/geometry.ts`, and verify unit tests for in/out classification at the lines
- [x] 5.4 Build `StagePanel` and the demo notice and verify tests that an unavailable court stage shows its reason and demo rallies show the notice
- [x] 5.5 Add `useReviewShortcuts` (J/K, Space, 1/2/0, ignored in text fields) with optimistic corrections and rollback, and verify tests for each key and for the error rollback
- [x] 5.6 Add `LayerMenu` (ball trail, court lines disabled until a court mapping exists) and verify toggling hides the layer

## 6. Layout, accessibility, performance

- [x] 6.1 Implement the desktop layout and the phone layout (stacked + tabs at < 768 px) and verify at 360 px width there is no horizontal scroll
- [x] 6.2 Verify keyboard-only use of both pages with visible focus, reduced-motion behaviour, and Lighthouse accessibility ≥ 90 on both pages
- [x] 6.3 Profile 10 s of playback and verify ≤ 50 commits outside the overlay canvas

## 7. Integration and docs

- [x] 7.1 Update the CI frontend job to Node 20, `npm ci`, `npm test`, `npm run build`, and verify the workflow file is valid YAML and the commands pass locally
- [x] 7.2 Update the web app README (run, test, layout) and `docs/architecture/ARCHITECTURE.md` (frontend section) and verify the documented commands run as written
- [x] 7.3 Walk through every PRD user story in `docs/prd/match-review.md` on the 5 demo clips and record the result in the change's verify notes

## 8. Visual system: analyst tool (owner feedback 2026-10-08)

- [x] 8.1 Replace tokens with the analyst-tool palette and Public Sans, add the persisted Light/Dark switch (light default), and verify `src/theme.test.ts` passes for both themes and the switch survives a reload
- [x] 8.2 Restyle the library as a plain table-like list with rules, plain-text demo label and accent progress bar, and verify by screenshot review in both themes at 1280 px and 360 px
- [x] 8.3 Restyle the match page: inline score header, rally table with ▲ / edited marks, rule-separated sections, line-art court map, slim timeline, bordered demo notice; verify existing tests still pass and by screenshot review in both themes at 1280 px and 360 px
- [x] 8.4 Remove the now-unused Badge / Barlow pieces and verify `npm run lint`, `npm test`, `npm run build` are clean

## 9. Visual revision 2: editor layout after soredemo-web (approved 2026-10-08)

- [x] 9.1 Tokens: system font stack, grey page + white window surfaces, lane hues, mono for machine-origin strings, light theme by default; verify `src/theme.test.ts` covers every text pair in both appearances
- [x] 9.2 Add `GET /videos/{id}/ball/coverage?bins=N` and verify backend tests for coverage values, bin count and the 404 before ball tracking ran; regenerate the frontend types
- [x] 9.3 Multi-lane timeline (Rallies A/B, Ball ticks, Landings, Review) with a playhead and click/drag to seek; verify component tests for lane content and seeking, and that playback still commits ≤ 5 times per second
- [x] 9.4 Inspector for the current rally (winner, end, confidence, landing, correction) with tabs for Rallies / Landings / Analysis; verify tests for the inspector rows and that 1 / 2 / 0 update it
- [x] 9.5 Editor window layout at desktop, stacked at phone width; verify screenshots in both appearances at 1280 and 360 px with no horizontal overflow

## Workflow follow-up

- Run `openspec validate rebuild-match-review-ui --strict` and the verify step before archiving.
- Archive the change so `openspec/specs/match-review-ui` and `video-library` reflect the new behaviour.
