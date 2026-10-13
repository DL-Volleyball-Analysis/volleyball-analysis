# Proposal

## Why
The repository works and is tested, but its layout, history and tooling show how it grew rather than how it is built
and changed: the pipeline lives in the web app and is reached through `sys.path`, `main.py` is 856 lines, generated
files are tracked, every commit goes straight to `main`, dependencies are unpinned and there is no type checking,
formatter, release or architecture record (PRD docs/prd/engineering-practice.md).

## What Changes
- **Layering**: `webapp/backend/pipeline.py` moves to `vball.pipeline` (registry, stage contract, one module per
  stage); the backend becomes the package `vball_app` (`api/` routers per resource, `schemas.py`, `db.py`,
  `worker.py`, `settings.py`); script-only logic used by tests moves into `vball`; all `sys.path` edits go.
- **Hygiene**: tracked evaluation outputs removed from git (kept on disk) and ignored.
- **Tooling**: `ruff format`; mypy on `vball` (strict for `vball.pipeline` and new modules); pre-commit; dependency
  groups in `pyproject.toml` with a pip-tools lock file used by CI; `.python-version` 3.12, extra CI job on 3.14.
- **Process**: direct commits to `main` (no pull requests, owner's decision) guarded by pre-commit and a local
  check script that mirrors CI; Conventional Commits;
  `CHANGELOG.md` and semantic-version tags with GitHub releases; `CONTRIBUTING.md`; Dependabot; `pip-audit` in CI.
- **Models**: `models/manifest.json` (file, SHA-256, source, result document); start-up check; `scripts/fetch_models.py`.
- **Operations**: `logging` instead of `print` in `vball` and the app; settings from environment variables; Dockerfile
  and `docker-compose.yml`.
- **Docs**: `docs/architecture.md`; ADRs in `docs/adr/`.
- **Planning debt**: open OpenSpec changes finished and archived or closed with a reason.

Out of scope: analysis features or accuracy, cloud or multi-user deployment, frontend rewrite. No pull requests or
branch protection (owner's decision, 2026-10-13).

## Capabilities

### New Capabilities
- `development-workflow`: how changes reach `main` and how a release and its models are identified.

### Modified Capabilities
- `analysis-jobs`: the pipeline is part of the analysis package and its results are reproducible across the move.

## Impact
`webapp/backend/*` (moved into `vball_app` and `vball.pipeline`), `scripts/*` (imports), tests (imports, one
regression test of stage outputs), `pyproject.toml`, `.github/`, new docs. No change to any API route, stage output
or the frontend.
