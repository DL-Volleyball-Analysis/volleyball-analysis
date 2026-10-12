## ADDED Requirements

### Requirement: Pipeline in the analysis package
The staged pipeline SHALL be part of the `vball` package (`vball.pipeline`) and be usable without the web app; the
web app, scripts and tests SHALL import it as a package, without editing `sys.path`.

#### Scenario: Script use
- **WHEN** a script runs analysis stages on a match
- **THEN** it imports `vball.pipeline` and the stages produce the same files the web app would

#### Scenario: Results unchanged by the move
- **WHEN** one fixed end-line clip and one broadcast clip are analysed before and after the move
- **THEN** every stage's JSON and CSV output is identical, ignoring timestamps
