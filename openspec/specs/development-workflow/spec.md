# development-workflow Specification

## Purpose
TBD - created by archiving change adopt-engineering-practices. Update Purpose after archive.

## Requirements

### Requirement: Every commit passes the checks
Every commit to `main` SHALL pass, locally before it is made and in CI after the push, the same checks: lint, format
check, type check, Python tests with coverage gates, dependency audit, and the frontend lint, tests and build.

#### Scenario: Failing check
- **WHEN** a change lowers vball coverage below 90% or adds a mypy error in `vball`
- **THEN** `scripts/check.sh` fails before the commit and the CI run of the push fails

#### Scenario: Commit message
- **WHEN** a commit is made
- **THEN** its subject follows Conventional Commits (`type(scope): summary`, at most 72 characters) and details go in
  the body

### Requirement: Reproducible environment
Development and CI SHALL install the same pinned dependency versions from the lock file on the same Python version.

#### Scenario: Fresh clone
- **WHEN** someone clones the repository and follows CONTRIBUTING.md or runs `docker compose up`
- **THEN** the tests pass and the app starts, with model weights fetched and checked against the manifest

### Requirement: Identified releases and models
Each release SHALL have a semantic-version tag, a GitHub release and a CHANGELOG entry; each model weight file SHALL
be listed in `models/manifest.json` with its SHA-256, source and the result document that measured it.

#### Scenario: Weight file changed
- **WHEN** a weight file on disk does not match its manifest checksum
- **THEN** the app logs an error naming the file at start and the stage that needs it reports it as unavailable

### Requirement: Generated files are not tracked
Evaluation outputs, caches and model weights SHALL NOT be committed.

#### Scenario: Evaluation run
- **WHEN** an evaluation script writes its results
- **THEN** they go under `outputs/` (ignored) and `git status` stays clean
