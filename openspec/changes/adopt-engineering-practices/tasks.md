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
- [ ] 3.1 `ruff format` + `.git-blame-ignore-revs`; verify `ruff format --check` in CI
- [ ] 3.2 mypy config (strict for vball.pipeline); fix errors; verify `mypy src/vball` clean in CI
- [ ] 3.3 Dependency groups, pip-tools lock, `.python-version`; CI installs from the lock, extra 3.14 job; verify CI green
- [ ] 3.4 pre-commit config; verify `pre-commit run --all-files`
- [ ] 3.5 `pip-audit` job and Dependabot (pip, npm, actions); verify the job runs

## 4. Process and release
- [ ] 4.1 CONTRIBUTING.md (setup, Conventional Commits, checks before a commit, OpenSpec), issue templates
- [ ] 4.2 `scripts/check.sh` running every CI check locally; verify it fails on a planted lint error and passes clean
- [ ] 4.3 CHANGELOG.md and tag v0.1.0 with a GitHub release; verify the release page

## 5. Models and operations
- [ ] 5.1 `models/manifest.json`, start-up check, `scripts/fetch_models.py`; tests for a missing and a changed file
- [ ] 5.2 `logging` in place of `print` in vball and the app; settings from environment; tests
- [ ] 5.3 Dockerfile and docker-compose.yml; verify `docker compose up` serves /health and the frontend

## 6. Documentation and planning debt
- [ ] 6.1 docs/architecture.md (components, data flow, stage contract, diagram); README links it
- [ ] 6.2 ADRs in docs/adr/, one file per decision named by slug (no number prefixes; date and status in the file): staged cached pipeline, court from painted lines, focal length from the net, leave-one-match-out evaluation, single-user local deployment
- [ ] 6.3 Each open OpenSpec change finished and archived or closed with its reason; verify `openspec list`
