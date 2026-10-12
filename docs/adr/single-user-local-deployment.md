# Single-user local deployment

Date: 2026-10-08 · Status: accepted

## Context
The users are a coach and the players of one team, reviewing their own recordings. Videos are large (1-3 GB per
match) and private; analysis needs the models and a few hours of CPU. The capstone design used Celery and Redis
for jobs, which nobody ran in practice.

## Decision
The system runs on the user's own computer: a FastAPI process, one worker process and a SQLite database in WAL mode
that holds videos, jobs, rallies, corrections and tags. The worker claims jobs with `UPDATE … RETURNING` and requeues
jobs left running after a crash. There are no accounts and no cloud services; local video files can be registered
without copying (`/videos/import`).

## Consequences
- Nothing to operate: no broker, no database server, no credentials; the data never leaves the machine.
- One analysis at a time. A team with many matches waits; this is acceptable for review after a match.
- Moving to several users would need authentication, a real job queue and object storage; the API shape (resources
  per video) does not have to change for that.

## Alternatives
- Celery + Redis, Postgres: needed for many users or machines, not for one.
- A hosted service: uploads of full matches, storage costs and privacy questions for no gain to one team.
