# Changelog

All notable changes to this project. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
and versions follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html). Numbers cite `docs/results/`.

## [Unreleased]

### Added
- Rallies stage version 3: still end-line cameras use the fixed-camera rally model (cues shared with its training
  script); on the six fixed clips it reproduces the offline result (F1 0.76).
- Rolling backups of the app database (`vball_app.backup`): at start and hourly after jobs, newest 10 kept, restore
  saves the current file first.
- Court error in metres from hand-labelled floor points: `scripts/eval_fixed_court.py` and a labelling page.

### Changed
- Fixed end-line courts measured on hand-labelled floor points: five of six right to 0.02-0.06 m (median); Quincy is
  wrong by 1.06 m. v0.1.0 said six of six by eye.

### Fixed
- The backend tests could reach the real `webapp/data` and emptied the local database; test data is now isolated with
  guards. The 11 analysed videos were restored with their results; user corrections and tags were lost.
- broadcast_back_view gets its court from line evidence and 16 3D flights (it had none).

## [0.1.0] - 2026-10-13

First release: the rebuilt analysis system after the capstone project, with its measurements.

### Analysis (`vball`)
- Staged, versioned and cached pipeline (`vball.pipeline`): decode, court, ball, players, actions, trajectory,
  events (not built yet), rallies; each stage reports `done` or `unavailable` with the reason.
- Camera motion by keyframe registration; court, corrections and 3D flights follow a panning camera.
- Court registration per camera shot with two keypoint models (held-out broadcast clips: median 0.10 m; gym images:
  0.49 m) and, for still cameras, a court fitted to the painted lines of a background plate (6 of 6 fixed end-line
  clips right by eye); focal length from the net tape on symmetric end-line views.
- Ball tracking with VballNet V4c; WASB fine-tuned on gym footage reaches F1 0.946 at 10 px on held-out gym matches
  (not yet in the pipeline: its broadcast test is pending).
- Players: detector fine-tuned on SportsMOT volleyball (IDF1 0.690, precision 0.970), court positions, teams and
  roles, at most 12 players on court.
- Actions per player from a classifier weighted by the ball's position (macro F1 0.678 on unseen matches) and
  shirt numbers voted over time.
- 3D ball flights: constrained ballistic fit anchored to the players at each touch (synthetic attacks: median error
  0.31 m instead of 0.76 m); real flights are flagged low quality while the 2D track is the bottleneck.
- Rally detection from the system's own cues: F1 0.742 on held-out broadcast matches; for fixed end-line cameras a
  model trained on score-bug labels of full matches reaches F1 0.76 on six fixed clips.
- Point changes read from the on-screen score (`vball.scorebug`) as free rally labels.

### Web app (`vball_app`, React frontend)
- FastAPI backend with one router per resource, SQLite job queue and a separate worker.
- Match review app: rallies, score, court and ball overlays, tactics board in 2D and 3D, coach tags and player
  statistics, court corrections per camera shot.
- Rendered analysis videos with court, players, ball, 2D map and 3D view.

### Engineering
- One package per concern: analysis in `vball` (pipeline, datasets, evaluation), web app in `vball_app`; scripts are
  command lines only and nothing edits `sys.path`.
- Pinned dependencies (`requirements/lock.txt`), CI on Python 3.14 and 3.12 with ruff, format check, mypy, tests
  with a 90% coverage gate (281 backend and analysis tests, 165 frontend tests), pip-audit and npm audit.
- Pre-commit hooks and `scripts/check.sh` with the same checks locally; `CONTRIBUTING.md`.
- Model weights listed in `models/manifest.json` with checksums, sources and the results that measured them; stages
  use only matching files.
- Architecture overview and decision records (`docs/architecture.md`, `docs/adr/`).

[Unreleased]: https://github.com/DL-Volleyball-Analysis/volleyball-analysis/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/DL-Volleyball-Analysis/volleyball-analysis/releases/tag/v0.1.0
