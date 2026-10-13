# Proposal

## Why
A test run emptied the local app database on 2026-10-13 and there was no backup; the user's corrections and tags were
lost (PRD docs/prd/engineering-practice.md, addendum "backups of the app database").

## What Changes
- `vball_app.backup`: SQLite online backups to `webapp/data/backups/webapp-<UTC time>.db`, newest 10 kept.
- The API and the worker back up at start; the worker also after a finished job when the newest backup is over an hour
  old.
- `python -m vball_app.backup --list | --restore <file>`: restoring first backs up the current database.

Out of scope: off-machine copies (the user's own backup tool covers the folder).

## Capabilities

### Modified Capabilities
- `analysis-jobs`: the job database is backed up and can be restored.

## Impact
`webapp/backend/vball_app/backup.py` (new), `main.py`, `worker.py`, tests, webapp README.
