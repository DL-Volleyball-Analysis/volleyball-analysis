# Tasks

## 1. Backend
- [ ] 1.1 Display name column and `PATCH /videos/{id}` (rename); derived default; tests
- [ ] 1.2 Thumbnail at import (and a backfill for existing videos); `GET /videos/{id}/thumbnail`; tests
- [ ] 1.3 `GET /videos/{id}/health` and `with=health` on the list: per item status, reason, fixing action; tests on
      the nine analysed videos' stage results as fixtures

## 2. Visual system
- [ ] 2.1 Tokens (light / dark), Barlow + Barlow Condensed via @fontsource, Lucide icons; theme test updated
- [ ] 2.2 Header with "Add match video" on every page

## 3. Library
- [ ] 3.1 Match cards (thumbnail, name, duration, date, state, result) and the drop card; upload progress
- [ ] 3.2 Rename and delete with confirmation; empty library state

## 4. Match page
- [ ] 4.1 Layout: video two thirds, inspector tabs (Health first), score only with rallies, plain demo notice
- [ ] 4.2 Overlay chips on the video, defaults from available results, disabled chips with reasons
- [ ] 4.3 Health panel with "Set court" opening the court picker on the shot
- [ ] 4.4 Timeline density strips, label collision rule, zoom and pan

## 5. Verify
- [ ] 5.1 Tests and coverage gates; Lighthouse accessibility 100; keyboard checks with Playwright
- [ ] 5.2 Screenshots of all nine videos (desktop, phone) reviewed; paper figures regenerated
