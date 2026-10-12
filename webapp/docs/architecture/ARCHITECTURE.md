# Architecture

```
 browser ──HTTP/SSE──► API (vball_app.main) ──SQLite──► worker (vball_app.worker)
                          │      ▲                              │
                          │      └── data/results/<video>/ ◄────┘ vball.pipeline ─► vball
                          └── data/uploads/
```

- **API** never runs analysis. It stores uploads, queues a job, and serves stage results.
- **Worker** claims the oldest queued job (`UPDATE … RETURNING`), runs the pipeline and writes
  progress to the job row. Jobs left `running` after a crash are re-queued on start.
- **Progress** reaches the browser through one SSE endpoint (`/videos/{id}/jobs/stream`).
- **SQLite in WAL mode** is enough for one machine; there is no Redis/Celery/Postgres.

## Pipeline
`decode → court → ball → players → actions → trajectory → events → rallies`, each writing `<stage>.json`
(version, status, summary). A rerun from stage S recomputes S and the stages after it and reuses earlier
results whose version matches, e.g. a new court model does not redo ball tracking.

| Stage | Output | Code |
|---|---|---|
| decode | fps, size, camera shots (HSV histogram cuts), camera motion | `vball.pipeline.stages.decode` |
| court | per-shot court keypoints and corners; two models, the better per shot | `vball.court_registration` |
| ball | `ball.csv` frame, visible, x, y | `vball.ball` (VballNet V4c) |
| players | `players.csv.gz` boxes, track ids, court positions, team and role | `vball.players`, `vball.teams` |
| actions | `action_events.json` actions per track, time-local shirt numbers | `vball.actions`, `vball.jersey` |
| trajectory | `flights.json` 3D ballistic flights with uncertainty | `vball.calibration`, `vball.trajectory` |
| events | contacts, landing point in metres | todo (M3) |
| rallies | rallies table: start/end, winner, reason, confidence | todo (M3) |

**Court corrections** live in their own table and are never written into `court.json`; the pipeline, the API
and the renderer overlay them when they read the court (`vball.pipeline.corrected_court` →
`vball.court_registration.apply_corrections`), so a rerun keeps them. Saving or clearing one queues a
re-analysis from `players`, the first stage that uses the court (court and ball results are reused).

## Data
| Table | Purpose |
|---|---|
| `videos` | file path and metadata |
| `jobs` | status, current stage, progress, error |
| `rallies` | model winner and the user's `winner_override`, kept separately so corrections can be used as labels to measure scoring accuracy |
| `rosters`, `tags` | players per team and the coach's attack / serve tags (statistics) |
| `dismissed_suggestions` | suggested tags the user rejected |
| `court_corrections` | per shot: four floor points the user clicked and which court points they are |

Scores are not stored; `vball.scoring.running_score` derives them from the rally winners
(25 points, 15 in the fifth set, 2-point lead).

## API
| Method | Path | |
|---|---|---|
| GET | `/health` | |
| GET / POST | `/videos` | list / upload (queues analysis) |
| POST | `/videos/import` | register a local file without copying |
| GET / DELETE | `/videos/{id}` | |
| GET | `/videos/{id}/file` | video with Range support |
| POST | `/videos/{id}/jobs` | rerun, optionally `from_stage` |
| GET | `/videos/{id}/jobs/latest`, `/jobs/stream` | job state, SSE |
| GET | `/videos/{id}/stages` | per-stage status and summary |
| GET | `/videos/{id}/court` | court per camera shot, corrections applied |
| PUT / DELETE | `/videos/{id}/court/{shot}` | set a shot's court from four clicked floor points (`preset`: corners or near half) / clear it |
| GET | `/videos/{id}/ball?start=&end=` | ball positions in a time window |
| GET | `/videos/{id}/ball/coverage?bins=` | share of frames with a detection per time bin (timeline ball lane) |
| GET | `/videos/{id}/players?start=&end=` | player boxes and court positions in a time window |
| GET | `/videos/{id}/flights?start=&end=` | 3D ball flights overlapping a time window |
| GET / PATCH | `/videos/{id}/rallies[/{idx}]` | rallies with running score; correct a winner |
| GET | `/videos/{id}/actions` | action events, shirt numbers and suggested tags |
| POST | `/videos/{id}/actions/suggestions/{sid}/dismiss` | reject a suggested tag |
| GET / PUT | `/videos/{id}/roster` | players per team |
| GET / POST | `/videos/{id}/tags` | coach tags |
| PATCH / DELETE | `/videos/{id}/tags/{tag_id}` | change or delete a tag |
| GET | `/videos/{id}/stats[?format=csv]` | player statistics |

Full schema: `/docs` (OpenAPI) on the running API.

## Frontend
React + Vite + TypeScript (strict), TanStack Query, React Router, Tailwind CSS v4, Vitest.

- **Types** come from the API: `npm run gen:api` writes `src/api/schema.d.ts` from `/openapi.json`;
  components use the aliases in `src/api/types.ts`. No hand-written response types.
- **Server state** lives in the query cache. Everything about one video is under `['video', id]`,
  so one invalidation refreshes its stages, rallies and ball windows.
- **Live progress**: `src/api/jobStream.ts` opens one EventSource per queued/running video and
  writes job events into the cache; on done/failed it closes and invalidates the video.
- **Playback time is not React state.** `src/playback/clock.ts` holds the `<video>`; the overlay
  canvas reads `currentTime` every animation frame, while components subscribe to time quantised
  to 200 ms (≤ 5 re-renders per second during playback).
- **Ball data** is fetched in 30 s windows around the playhead (`/ball?start&end`).
- **Corrections** are optimistic and rolled back with a notice if the server rejects them.
- **Editor layout**: the match page is one window: video, a rally inspector, tabs (rallies / landings /
  analysis) and a multi-lane timeline whose playhead moves in an animation frame, outside React.
- **Design tokens** in `src/theme.css` (light by default, dark on request), system fonts, mono only for
  machine-origin strings; team and in/out are never shown by colour alone.

```
src/api  src/playback  src/library  src/match  src/court  src/ui
```
Folders follow features: a change to the court map touches `src/court` only.
