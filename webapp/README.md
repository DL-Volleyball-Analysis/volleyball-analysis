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
| `court` – keypoints → homography per shot, best of the installed court models | done (2 of 5 evaluation clips usable) |
| `ball` – VballNet V4c tracking | done |
| `players` – YOLO26s fine-tuned on SportsMOT to box players only + BoT-SORT, court positions, team and role, 12-player cap | done (IDF1 0.690) |
| `actions` – action events per player, time-local shirt numbers | done (needs `models/action_yolo11m.pt`, `models/jersey_digits_yolo26s.pt`) |
| `trajectory` – camera calibration, bounded and player-anchored 3D flights | done (flights on real clips still low quality) |
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
  src/stats/      tagging (entry, shortcuts, inspector), statistics tab, roster editor
  src/board/      tactics board: 2D (SVG) and 3D (three.js, loaded when opened) ball flights
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
J / K previous / next rally · Space play / pause · 1 / 2 winner A / B · 0 clear correction ·
T / S tag an attack / serve at the playhead (then the player number, A / B to switch team, Enter)

## Analysis video
`../.venv/bin/python backend/render.py <video name or id> [--out file.mp4]` draws every result on the video for
sharing outside the app: ball trail, player boxes and ids, court lines (only for shots whose court status is
ok), a court map with the players' positions (and the ball from 3D flights), and a status bar that says what is
missing and why. Default output: `data/results/<id>/<name>_analysis.mp4` (H.264 when ffmpeg is installed).

## Tactics board
The Board tab shows the 3D ball flights of the rally at the playhead, from above (2D) or as a rotatable
3D court. Height is the depth of one hue with labels at the apex and the net crossing; low-quality
flights are dashed with their reason on hover or focus; frames the camera did not see are dotted. Flights
come from the trajectory stage, which needs a calibrated camera (court keypoints); videos with demo rallies
show demo flights, labelled as such.

## Statistics
The Stats tab turns attack and serve tags into per-player and per-team statistics, per set or for the
match, with a CSV export: attempts, kills, errors, attack efficiency = (kills − errors) / decided attempts,
kill rate, serves, aces and serve errors. The last tag of a rally takes its outcome from the rally's
winner (corrections included) unless set by hand; earlier tags are in play. Tags of rallies without a
winner are left out of the ratios and the line is marked incomplete. Tags are stored by time, so they
survive re-analysis. Rules and tests: `vball.stats` (`tests/test_stats.py`).

## Actions, shirt numbers and suggested tags
The actions stage runs the action model at 10 fps and assigns each action box to the player track it overlaps
most (`vball.actions`); the timeline's Actions lane shows them (Srv, Rec, Set, Spk, Blk) in the team's colour. Shirt
numbers are read from digit detections on the upper part of each player box at 2 fps and voted over the readings
within a second (`vball.jersey`), so a label follows a tracker identity switch; players without a clear vote are
shown as `ID n`, never a guessed number. Spikes and serves become suggested attack / serve tags, dashed in the
Tags lane: accepting posts an ordinary tag (the number must be given when it was not read), dismissing is
remembered, and nothing counts in statistics until accepted. Accuracy: `docs/results/actions.md`.

## License
MIT. Court keypoint data: Roboflow Universe sets (CC BY 4.0).

*National Taiwan Ocean University – Department of Computer Science, senior capstone.*
