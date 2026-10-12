# Tasks

## 1. Hygiene and baseline
- [x] 1.1 Untrack `test_*court_kpt*.pt.json` (move to outputs/court/eval), ignore them; verify `git ls-files` and a clean `git status`
- [x] 1.2 Golden stage outputs for fixed_hawaii_irvine (60 s) and broadcast_side_rally; `scripts/compare_stage_outputs.py`; verify it reports identical on a rerun

## 2. Layering
- [x] 2.1 `vball.pipeline` package (config, stages, corrections, registry) moved from webapp/backend/pipeline.py; tests moved; verify golden identical and all tests pass
- [x] 2.2 `render` stays in the web app (it reads the user's court corrections from the database) and moves with it into `vball_app.render`; verify test_render
- [x] 2.3 Backend package `vball_app` with routers per resource and `schemas.py`; verify API tests unchanged and OpenAPI schema identical (diff of /openapi.json)
- [x] 2.4 Script logic moved into `vball.datasets` / `vball.evaluation` / `vball.pipeline.compare` (scripts keep `main()`), tests for it; all `sys.path` edits removed; verify `grep -r sys.path src scripts webapp/backend tests` is empty and every script's `--help` runs

## 3. Tooling
- [x] 3.1 `ruff format` + `.git-blame-ignore-revs`; verify `ruff format --check` in CI
- [x] 3.2 mypy over vball and vball_app, zero errors; modules with errors at introduction listed as type debt in pyproject.toml (can only shrink); verify `mypy` clean in CI
- [x] 3.3 Dependency groups (ml, dev extras), `requirements/lock.txt` from `scripts/lock.sh` (pip freeze of a clean environment; pip-tools cannot resolve the local vball dependency), `.python-version` 3.14; CI installs from the lock on 3.14 and 3.12; tests made hermetic (no real weights from models/); verify CI green
- [x] 3.4 pre-commit config; verify `pre-commit run --all-files`
- [x] 3.5 `pip-audit` and `npm audit` in CI (no Dependabot: it works through pull requests, which the owner does not want); verify the jobs run

## 4. Process and release
- [x] 4.1 CONTRIBUTING.md (setup, Conventional Commits, checks before a commit, OpenSpec), issue templates
- [x] 4.2 `scripts/check.sh` running every CI check locally; verify it fails on a planted lint error and passes clean
- [x] 4.3 CHANGELOG.md and tag v0.1.0 with a GitHub release; verify the release page

## 5. Models and operations
- [x] 5.1 `models/manifest.json` (vball.manifest), start-up check in the API and the worker, stages use only files matching it, `scripts/fetch_models.py`; tests for a missing and a changed file
- [x] 5.2 `logging` in place of `print` in vball and the app; settings from environment; tests
- [ ] 5.3 Dockerfile and docker-compose.yml; verify `docker compose up` serves /health and the frontend

## 6. Documentation and planning debt
- [x] 6.1 docs/architecture.md (components, data flow, stage contract, diagram); README links it
- [x] 6.2 ADRs in docs/adr/, one file per decision named by slug (no number prefixes; date and status in the file): staged cached pipeline, court from painted lines, focal length from the net, leave-one-match-out evaluation, single-user local deployment
- [x] 6.3 Each open OpenSpec change finished and archived or closed with its reason; verify `openspec list`
  (archived with reasons for the closed tasks: add-court-registration, add-rally-detection, measure-ball-and-actors,
  add-ball-trajectory-3d, whose stage-order delta was rebuilt on the current spec; still open because work continues:
  label-rallies-from-score, train-ball-detector (Kaggle quota), verify-court-by-lines, redesign-review-experience (waiting for the owner's OK))
