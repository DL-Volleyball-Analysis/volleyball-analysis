# Capstone web app: current-state analysis

Subject: `DL-Volleyball-Analysis/volleyball_analysis_webapp` (renamed `capstone-webapp`, archived) as of its 2026-01 `main` branch (read from code, not from its docs). Written 2026-10-07; the redesign goals, requirements and plans that followed now live in:

- Product requirements: [`docs/prd/match-review.md`](prd/match-review.md) and [`docs/prd/README.md`](prd/README.md)
- Backend behaviour (implemented on branch `redesign`): `openspec/specs/{video-library,analysis-jobs,match-scoring}`
- Frontend plan: `openspec/changes/rebuild-match-review-ui/`

## System design
| Item | Docs said | Code did |
|---|---|---|
| Task queue | Celery + Redis | FastAPI `BackgroundTasks` inside the API process (`backend/main.py:402`, comment: "should use Celery in production"); the Celery worker in `ai_core/worker.py` was never called |
| Task state | stored in DB | `analysis_tasks = {}` in API memory (`main.py:143`): lost on restart, videos stuck in `processing` |
| Database | SQLite / PostgreSQL | SQLite only; `docker-compose.yml` set a Postgres `DATABASE_URL` (password `password`) that no code read |
| Progress | WebSocket | two WebSocket endpoints plus `setInterval` polling in the frontend |
| Results | — | one large JSON per video (per-frame boxes, actions, ball), loaded whole by the frontend |
| Analysis code | — | `ai_core/processor.py`, 85 KB, one class mixing ball, players, actions, jerseys and rally logic |

## Correctness (relevant to our goals)
- **Scoring never worked:** `results["scores"]` was only appended for action types `score` / `spike_score` / `attack_score` (`processor.py:1590`), but the action model has only spike / set / receive / serve / block.
- **Rally detection too coarse:** "Play if any action or ball is detected in this frame" (`processor.py:1694`); one false detection starts a rally, one missed ball ends it.
- **No court coordinates:** no homography, landing or in/out; the separate court repo used fixed pixel thresholds.
- **Old ball model:** VballNetV1 grayscale, padding the 9-frame buffer with copies of the first frame (`processor.py:185`).

## Frontend
- Create React App (`react-scripts` 5, unmaintained), TypeScript 4.9.
- `VideoPlayer.tsx` 36 KB, result typed `any`, a dozen `useState` toggles.
- `requestAnimationFrame` called `setCurrentTime` every 16 ms (`VideoPlayer.tsx:284`): the whole player tree re-rendered ~60 times per second.
- Flow was "upload → wait → watch overlays"; no score, rally list or landing map.
- Privacy / Terms / Support pages in a local tool; footer GitHub link pointed at another account's repo.

**Worth keeping as ideas:** Tailwind, the event timeline and heatmap interactions, the manual jersey-number tagging flow.
