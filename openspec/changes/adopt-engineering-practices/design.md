# Design

## Context
`webapp/backend/` is a folder of top-level modules (`main`, `pipeline`, `render`, `database`, `worker`, `settings`,
`demo`) imported by bare name, so scripts and tests put the folder on `sys.path`. The pipeline orchestrates `vball`
modules and owns the stage contract (`STAGES`, `FUNCS`, `VERSIONS`, `run`, `load_stage`), which is analysis, not web.

## Decisions

### D1. Package layout
```
src/vball/pipeline/          # owner: analysis package
  __init__.py                # run, load_stage, stage_file, STAGES, VERSIONS (public API)
  config.py                  # model paths, detector settings, rates (was module constants)
  stages/decode.py court.py ball.py players.py actions.py trajectory.py rallies.py
  models.py                  # adapters that load trained weights (what tests replace)
  results.py                 # the results folder: stage files, corrected_court, shared readers
  compare.py                 # compare two results folders (design D2)
src/vball/datasets/          # dataset builders (were scripts/build_*.py)
src/vball/evaluation/        # evaluation drivers (were scripts/eval_*.py, train_fixed_rallies.py)
webapp/backend/vball_app/    # owner: web app
  main.py                    # FastAPI app, middleware and routers only
  api/videos.py jobs.py court.py tracks.py rallies.py actions.py stats.py
  schemas.py  deps.py  db.py  worker.py  settings.py  render.py  demo.py
```
The renderer stays in the web app: it overlays the user's court corrections, which live in the app's database.
Scripts keep their `main()` (argument parsing); everything a test or another script uses lives in the package.
The backend is installed as its own small distribution (`webapp/backend/pyproject.toml`, name `vball-app`) depending
on `vball`. Run with `uvicorn vball_app.main:app`.

### D2. Behaviour preserved by a golden test
Before moving anything, the stage outputs of `fixed_hawaii_irvine` (first 60 s) and `broadcast_side_rally` are
stored under `outputs/golden/` (local, large). After each move step a script (`scripts/compare_stage_outputs.py`)
compares JSON (keys and values, timestamps ignored) and CSV (exact). CI keeps a small synthetic golden test that runs
the stage registry on fakes. Stage versions do not change, so caches stay valid.

### D3. Moves happen in a git worktree
The full-match extraction running in the background imports `pipeline` from the main checkout; the refactor is done
in a separate worktree on a local branch so that run is not disturbed, and fast-forwarded into `main` after it ends.

### D4. Tooling choices
- Formatter: `ruff format` (line length stays 150); the one-time reformat commit goes in `.git-blame-ignore-revs`.
- Types: mypy, `strict` for `vball.pipeline` and new modules, default elsewhere, with per-module ignores recorded in
  `pyproject.toml` and removed over time.
- Lock: pip-tools (`requirements/lock.txt` from `pyproject.toml` groups `dev`, `ml`, `app`); `uv` is not installed.
- Hooks: pre-commit with ruff, ruff-format, mypy, end-of-file and large-file checks.

### D5. Process
Direct commits to `main`, no pull requests or branch protection (owner, 2026-10-13). Each commit is guarded by
pre-commit (fast checks) and `scripts/check.sh` (everything CI runs). Conventional Commits (`feat`, `fix`,
`refactor`, `docs`, `test`, `build`, `ci`, `chore`); tags and CHANGELOG written by hand per release.

### D6. Logging and settings
`logging.getLogger(__name__)` in `vball` and the app; scripts configure it (`--verbose`). Settings: one
`pydantic-settings` object in `vball_app.settings` (`VBALL_DATA`, `VBALL_MODELS`, `VBALL_LOG_LEVEL`), pipeline
config passed in rather than read from globals where a stage needs it.

### D7. Model manifest
`models/manifest.json`: `{file, sha256, bytes, source, measured_in}`. `scripts/fetch_models.py` downloads files that
have a public URL (GitHub release assets of this repo) and verifies checksums; the app checks at start and the
stages report a missing or changed file as unavailable (existing behaviour for missing weights).

## Risks
- A move changes behaviour silently → golden comparison after every step (D2).
- Big diffs hide changes → move commits contain moves and import edits only; logic edits go in separate commits.
- mypy noise → gradual strictness (D4).
