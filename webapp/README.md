# Volleyball Analysis Web App | 排球分析網頁系統

Upload a match video, get ball tracking, court registration, rallies and the running score,
and review/correct them in the browser. Continuation of the NTOU capstone (DL-Volleyball-Analysis).

> **Branch `redesign` (work in progress).** Backend rewritten around a staged pipeline; new
> React frontend (library + match review). Rallies are demo data until rally detection lands.
> The capstone version is on `main`.

## Status
| Stage | State |
|---|---|
| `decode` – metadata, camera shot cuts | done |
| `court` – keypoints → homography | waiting for the court keypoint model |
| `ball` – VballNet V4c tracking | done |
| `events` – contacts, landing in court metres | todo |
| `rallies` – rally segmentation, point winner | todo (demo data only) |

## Layout
```
backend/
  main.py       HTTP API (FastAPI); only queues jobs and reads results
  worker.py     runs queued jobs, one at a time
  pipeline.py   analysis stages, cached per stage under data/results/<video_id>/
  database.py   SQLite: videos, jobs, rallies (+ user corrections)
  settings.py   data paths (VBALL_WEBAPP_DATA)
  demo.py       import the evaluation clips with placeholder rallies
  tests/
frontend/       React + Vite + TypeScript
  src/api/        fetch client, generated OpenAPI types, query hooks, live job stream (SSE)
  src/playback/   playback clock (time outside React state), rally at playhead
  src/library/    library page: upload, live progress, score summary
  src/match/      match page: scoreboard, video + overlay canvas, rally list/timeline, shortcuts
  src/court/      court geometry and the to-scale court map
  src/ui/         small shared pieces; theme.css holds the design tokens
docs/architecture/ARCHITECTURE.md
```
All analysis code lives in the `vball` package at the repository root (`src/vball/`); the web app
does not keep its own copy. Model weights go in the root `models/` folder.

## Run
From the repository root:
```bash
python -m venv .venv && .venv/bin/python -m pip install -e . -r webapp/requirements.txt
cd webapp

../.venv/bin/uvicorn --app-dir backend main:app --reload        # API on :8000, docs at /docs
../.venv/bin/python backend/worker.py                            # analysis worker
../.venv/bin/python backend/demo.py                              # optional: import sample clips

cd frontend && npm install && npm run dev                     # UI on http://localhost:5173 (proxies /api to :8000)
```
After changing backend models, regenerate the frontend types with the API running:
`cd frontend && npm run gen:api`.

## Test
```bash
../.venv/bin/python -m pytest backend/tests
cd frontend && npm test && npm run build
```
Frontend tests include WCAG contrast checks of the theme tokens (`src/theme.test.ts`).

## Keyboard (match page)
J / K previous / next rally · Space play / pause · 1 / 2 winner A / B · 0 clear correction

## License
MIT. Court keypoint data: Roboflow Universe sets (CC BY 4.0).

*National Taiwan Ocean University – Department of Computer Science, senior capstone.*
