# Architecture

```
 browser ──HTTP/SSE──► API (backend/main.py) ──SQLite──► worker (backend/worker.py)
                          │      ▲                              │
                          │      └── data/results/<video>/ ◄────┘ pipeline.py ─► vball
                          └── data/uploads/
```

- **API** never runs analysis. It stores uploads, queues a job, and serves stage results.
- **Worker** claims the oldest queued job (`UPDATE … RETURNING`), runs the pipeline and writes
  progress to the job row. Jobs left `running` after a crash are re-queued on start.
- **Progress** reaches the browser through one SSE endpoint (`/videos/{id}/jobs/stream`).
- **SQLite in WAL mode** is enough for one machine; there is no Redis/Celery/Postgres.

## Pipeline
`decode → court → ball → events → rallies`, each writing `<stage>.json` (version, status,
summary). A rerun from stage S recomputes S and the stages after it and reuses earlier results
whose version matches, e.g. a new court model does not redo ball tracking.

| Stage | Output | Code |
|---|---|---|
| decode | fps, size, camera shots (HSV histogram cuts) | `pipeline.decode` |
| court | per-shot homography | `vball.court_keypoints` (todo) |
| ball | `ball.csv` frame, visible, x, y | `vball.ball` (VballNet V4c) |
| events | contacts, landing point in metres | `vball.court` (todo) |
| rallies | rallies table: start/end, winner, reason, confidence | todo |

## Data
| Table | Purpose |
|---|---|
| `videos` | file path and metadata |
| `jobs` | status, current stage, progress, error |
| `rallies` | model winner and the user's `winner_override`, kept separately so corrections can be used as labels to measure scoring accuracy |

Scores are not stored; `vball.scoring.running_score` derives them from the rally winners
(25 points, 15 in the fifth set, 2-point lead).

## API
| Method | Path | |
|---|---|---|
| GET / POST | `/videos` | list / upload (queues analysis) |
| POST | `/videos/import` | register a local file without copying |
| GET / DELETE | `/videos/{id}` | |
| GET | `/videos/{id}/file` | video with Range support |
| POST | `/videos/{id}/jobs` | rerun, optionally `from_stage` |
| GET | `/videos/{id}/jobs/latest`, `/jobs/stream` | job state, SSE |
| GET | `/videos/{id}/stages` | per-stage status and summary |
| GET | `/videos/{id}/ball?start=&end=` | ball positions in a time window |
| GET | `/videos/{id}/ball/coverage?bins=` | share of frames with a detection per time bin (timeline ball lane) |
| GET / PATCH | `/videos/{id}/rallies[/{idx}]` | rallies with running score; correct a winner |

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
