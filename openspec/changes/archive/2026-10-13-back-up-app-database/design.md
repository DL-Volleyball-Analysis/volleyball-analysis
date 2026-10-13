# Design

- `sqlite3.Connection.backup` copies a live WAL database consistently; no locking of the app is needed.
- Files are named by UTC time (`webapp-20261013T120400Z.db`), so sorting by name is sorting by age.
- Owner: `vball_app.backup` (the database is the web app's; analysis results are files and are reproducible).
- Hourly limit in the worker: compare the newest file's time, so a burst of short jobs makes one backup.
