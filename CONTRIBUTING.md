# Contributing

How this repository is set up, changed and checked. The architecture is described in
[docs/architecture.md](docs/architecture.md); product requirements are in [docs/prd/](docs/prd/README.md).

## Setup
Python 3.14 (`.python-version`; 3.12 is the oldest supported) and Node 22 for the web app's frontend.

```bash
python3.14 -m venv .venv
.venv/bin/python -m pip install -r requirements/lock.txt   # pinned versions, the same CI installs
.venv/bin/python -m pip install -e ".[ml]" -e webapp/backend # the two packages, plus YOLO for real analysis
.venv/bin/pre-commit install                                # fast checks before every commit
cd webapp/frontend && npm ci
```

Model weights are not in git. `models/` holds the files listed in [docs/results/](docs/results/); the tests never
need them. Third-party code is cloned into `external/` and never edited (see the README).

## Layout
| Path | What lives there |
|---|---|
| `src/vball/` | the analysis package: every algorithm, the staged pipeline (`vball.pipeline`), dataset builders (`vball.datasets`) and evaluation drivers (`vball.evaluation`) |
| `webapp/backend/vball_app/` | the web app backend: FastAPI routers per resource, job worker, video render |
| `webapp/frontend/` | the React review app |
| `scripts/` | command lines only: argument parsing, then a call into `vball` |
| `training/`, `notebooks/` | GPU training code and notebooks, run on Kaggle / Colab |
| `tests/`, `webapp/backend/tests/` | pytest suites, run together from the repository root |

Code that a test or a second script needs belongs in a package, not in `scripts/`. Nothing edits `sys.path`.

## Making a change
1. **Plan first.** A feature or a behaviour change starts as a PRD section in `docs/prd/` and an OpenSpec change
   (`openspec/changes/<name>/`: proposal, specs, design, tasks). Implement task by task, tick each task with the
   check that verified it, and archive the change when it is done (`openspec/specs/` describes current behaviour).
2. **Keep results honest.** A number goes into `docs/results/` with how it was measured: labelled data, synthetic
   data, or a label-free proxy. A refactor must not change results: compare the stage outputs before and after with
   `scripts/compare_stage_outputs.py`.
3. **Check locally.** `pre-commit` runs ruff, the format check and mypy on each commit. Before pushing, run
   `scripts/check.sh` (everything CI runs: lint, format, types, tests with the 90% coverage gate, dependency audit,
   frontend lint, tests and build).
4. **Commit** straight to `main` (no pull requests) with a [Conventional Commits](https://www.conventionalcommits.org)
   message: `type(scope): summary` in at most 72 characters, details in the body.
   Types: `feat`, `fix`, `refactor`, `perf`, `test`, `docs`, `build`, `ci`, `style`, `chore`.
5. **Push**; CI repeats the checks on Python 3.14 and 3.12.

## Dependencies
Runtime dependencies are declared in `pyproject.toml` (extras `ml` and `dev`) and `webapp/backend/pyproject.toml`.
After changing them, regenerate the pins with `scripts/lock.sh` and commit `requirements/lock.txt`.

## Types
mypy checks `vball` and `vball_app` with no errors. Modules that had errors when mypy was introduced are listed as type
debt in `pyproject.toml`; fix one and remove it from the list, never add to it.

## Releases
Versions follow [Semantic Versioning](https://semver.org). A release gets an entry in `CHANGELOG.md`, the same version
in both `pyproject.toml` files, an annotated tag `vX.Y.Z` and a GitHub release with the changelog entry.
