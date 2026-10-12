# Engineering practice: a repository that works like an industry project

Version 1.0 · 2026-10-13 · Owner: YuJia Liang · Parent: [README.md](README.md)

## Why
The analysis works and is tested (about 400 tests, coverage gates in CI), but the repository still shows how it grew
rather than how it is meant to be built and changed. Reviewers (graduate-school interviewers, possible employers,
future contributors) read the code layout, the history and the tooling before any result. A review on 2026-10-13
found:

| Area | Finding |
|---|---|
| Layering | The analysis pipeline (`webapp/backend/pipeline.py`, 604 lines) lives in the web app; ten scripts reach it or `src/` through `sys.path.insert`. Script-only logic (`weak_labels`, `match_ends`) is imported by tests. |
| Web backend | `main.py` holds 856 lines: schemas, every route and helpers. The backend is a folder of top-level modules, not a package. |
| Repository | Four evaluation outputs (`test_*court_kpt*.pt.json`) are committed at the root. |
| Process | 128 commits straight to `main`, no branches or pull requests; commit subjects up to 246 characters; no tags, releases or changelog. |
| Planning | Eight OpenSpec changes open, two of them at 28/30 and 15/19 tasks for days. |
| Reproducibility | Dependencies unpinned; local Python 3.14 vs CI 3.12; model weights identified only by file name; no type checking; no formatter. |
| Operations | Progress and errors go through `print`; settings are module constants; the web app runs only from a developer checkout. |

## What
1. **Layering**: the pipeline becomes part of the `vball` package (`vball.pipeline`, one module per stage plus the
   stage registry). The web backend becomes a package with routers per resource and a schema module. No
   `sys.path` manipulation anywhere; scripts are thin command lines over `vball`.
2. **Repository hygiene**: no generated files tracked; `.gitignore` covers them.
3. **Tooling**: `ruff format` as the single formatter; type checking of `vball` with mypy (gradual, strict for new
   modules); pre-commit hooks for both; dependency groups in `pyproject.toml` and a pinned lock file used by CI;
   one Python version (3.12) pinned for development and CI, with 3.14 as an extra CI job.
4. **Process**: commits go to `main` directly (owner's decision, 2026-10-13: no pull requests); the same checks as
   CI run before each commit through pre-commit and a `make check`-style script; Conventional Commits;
   semantic-version tags with GitHub releases and a `CHANGELOG.md`; `CONTRIBUTING.md`; Dependabot and a dependency
   audit in CI.
5. **Models**: `models/manifest.json` lists every weight file with its SHA-256, source and the result document that
   measured it; the app checks it at start and a script fetches what is missing.
6. **Operations**: standard `logging` in place of `print` in library and app code; settings from environment
   variables (one settings object); a Dockerfile and `docker compose` for the web app.
7. **Documentation**: `docs/architecture.md` (components, data flow, stage contract) and Architecture Decision
   Records in `docs/adr/` for the decisions already taken (staged cached pipeline, court from painted lines, focal
   length from the net, leave-one-match-out evaluation, single-user local deployment).
8. **Planning debt**: each open OpenSpec change is finished and archived, or closed with the reason written down.

## Success
- `grep -r "sys.path" src scripts webapp tests` finds nothing; `pipeline.py` and `main.py` are gone, no module over
  400 lines in `vball.pipeline` or the backend package.
- Every analysis result is unchanged: the stage outputs of one fixed clip and one broadcast clip are identical before
  and after the move (same JSON and CSV, ignoring timestamps).
- CI on every push runs lint, format check, mypy, tests with coverage gates, dependency audit and the frontend
  checks; the same checks run locally before each commit.
- A fresh clone runs the app with `docker compose up` (weights fetched by the script) or with the documented
  `pip install` steps.
- A first release `v0.1.0` with a changelog.

## Out of scope
- New analysis features or accuracy work.
- Cloud deployment, accounts, multi-user operation (PRD §7 Q1 stays: single-user, local).
- Rewriting the frontend (it already has lint, tests and a typed API client).
