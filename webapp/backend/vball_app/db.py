"""SQLite storage: videos, analysis jobs, rallies, rosters and action tags.

The API and the worker are separate processes, so the job queue lives here (WAL mode) instead
of in API memory. Rallies keep the model's winner and the user's correction side by side; the
corrections double as labels for measuring scoring accuracy. Rosters and tags are user data: re-analysis
never touches them, and tags are keyed by video time, not by rally (see vball.stats).
"""

import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS videos (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    path TEXT NOT NULL,
    fps REAL, frames INTEGER, width INTEGER, height INTEGER,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS jobs (
    id TEXT PRIMARY KEY,
    video_id TEXT NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
    status TEXT NOT NULL,              -- queued | running | done | failed
    from_stage TEXT NOT NULL,
    stage TEXT,                        -- stage currently running
    progress REAL NOT NULL DEFAULT 0,  -- 0..1 over the whole pipeline
    error TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    worker_id TEXT,                    -- the worker holding the job while running
    lease_until TEXT,                  -- the holder renews it; after it passes, another worker may take the job
    attempts INTEGER NOT NULL DEFAULT 0,  -- times the job was claimed
    timings TEXT                       -- JSON {stage: seconds} of the stages the last run computed
);
CREATE INDEX IF NOT EXISTS jobs_by_video ON jobs(video_id, created_at);
CREATE TABLE IF NOT EXISTS rallies (
    video_id TEXT NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
    idx INTEGER NOT NULL,
    start_s REAL NOT NULL,
    end_s REAL NOT NULL,
    winner TEXT,                       -- model output: 'a' | 'b' | NULL
    reason TEXT,                       -- in | out | net | fault | unknown
    confidence REAL,
    winner_override TEXT,              -- user correction: 'a' | 'b' | NULL
    landing_x REAL, landing_y REAL,    -- court metres (court.py frame), NULL if unknown
    source TEXT NOT NULL DEFAULT 'model',  -- model | demo
    PRIMARY KEY (video_id, idx)
);
CREATE TABLE IF NOT EXISTS rosters (
    video_id TEXT NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
    team TEXT NOT NULL,                -- 'a' | 'b'
    number INTEGER NOT NULL,
    name TEXT,
    PRIMARY KEY (video_id, team, number)
);
CREATE TABLE IF NOT EXISTS tags (
    id TEXT PRIMARY KEY,
    video_id TEXT NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
    time_s REAL NOT NULL,
    kind TEXT NOT NULL,                -- attack | serve
    team TEXT NOT NULL,                -- 'a' | 'b'
    number INTEGER NOT NULL,
    outcome TEXT,                      -- user outcome; NULL = inferred (vball.stats)
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS tags_by_video ON tags(video_id, time_s);
CREATE TABLE IF NOT EXISTS dismissed_suggestions (
    video_id TEXT NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
    suggestion_id TEXT NOT NULL,       -- '<kind>-<start frame>-<track id>' from the actions stage
    PRIMARY KEY (video_id, suggestion_id)
);
CREATE TABLE IF NOT EXISTS court_corrections (
    video_id TEXT NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
    shot INTEGER NOT NULL,             -- index into court.json shots
    frame INTEGER NOT NULL,            -- the frame the points were given at
    points_px TEXT NOT NULL,           -- JSON [[x, y] x 4], image pixels
    ids TEXT NOT NULL,                 -- JSON [4 K6Y7R floor ids] the points are (vball.court_registration.CORRECTION_PRESETS)
    created_at TEXT NOT NULL,
    PRIMARY KEY (video_id, shot)
);
"""

FINISHED = ("done", "failed")
LEASE_S = 60.0  # a worker renews its lease every LEASE_S / 3 (vball_app.worker)
MAX_ATTEMPTS = 3  # a job whose lease expired this many times fails instead of killing a fourth worker
JOB_COLUMNS = {  # added after the first release; created by the start-up migration on older databases
    "worker_id": "TEXT",
    "lease_until": "TEXT",
    "attempts": "INTEGER NOT NULL DEFAULT 0",
    "timings": "TEXT",
}


def job_row(row) -> dict | None:
    """A jobs row as a dict with `timings` decoded."""
    if row is None:
        return None
    job = dict(row)
    job["timings"] = json.loads(job["timings"]) if job.get("timings") else None
    return job


def now(after_s: float = 0.0) -> str:
    """UTC time as ISO text, which orders correctly as a string (all times in the database use it)."""
    return (datetime.now(UTC) + timedelta(seconds=after_s)).isoformat(timespec="milliseconds")


class Database:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as c:
            c.execute("PRAGMA journal_mode=WAL")
            cols = {r[1] for r in c.execute("PRAGMA table_info(court_corrections)")}
            if "corners_px" in cols:  # first draft of the table (2026-10-11, never released): no data to keep
                c.execute("DROP TABLE court_corrections")
            c.executescript(SCHEMA)
            have = {r[1] for r in c.execute("PRAGMA table_info(jobs)")}
            for col, decl in JOB_COLUMNS.items():
                if col not in have:
                    c.execute(f"ALTER TABLE jobs ADD COLUMN {col} {decl}")

    @contextmanager
    def connect(self):
        conn = sqlite3.connect(self.path, timeout=30)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    # videos
    def add_video(self, name: str, path: str, meta: dict) -> dict:
        vid = uuid.uuid4().hex[:12]
        with self.connect() as c:
            c.execute(
                "INSERT INTO videos VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (vid, name, path, meta.get("fps"), meta.get("frames"), meta.get("width"), meta.get("height"), now()),
            )
        v = self.get_video(vid)
        assert v is not None  # just inserted
        return v

    def get_video(self, vid: str) -> dict | None:
        with self.connect() as c:
            row = c.execute("SELECT * FROM videos WHERE id = ?", (vid,)).fetchone()
        return dict(row) if row else None

    def list_videos(self) -> list[dict]:
        with self.connect() as c:
            rows = c.execute("SELECT * FROM videos ORDER BY created_at DESC").fetchall()
        return [dict(r) for r in rows]

    def delete_video(self, vid: str) -> None:
        with self.connect() as c:
            c.execute("DELETE FROM videos WHERE id = ?", (vid,))

    # jobs
    def add_job(self, video_id: str, from_stage: str) -> dict:
        jid = uuid.uuid4().hex[:12]
        t = now()
        with self.connect() as c:
            c.execute(
                "INSERT INTO jobs (id, video_id, status, from_stage, created_at, updated_at) "
                "VALUES (?, ?, 'queued', ?, ?, ?)",
                (jid, video_id, from_stage, t, t),
            )
        job = self.get_job(jid)
        assert job is not None  # just inserted
        return job

    def get_job(self, jid: str) -> dict | None:
        with self.connect() as c:
            row = c.execute("SELECT * FROM jobs WHERE id = ?", (jid,)).fetchone()
        return job_row(row)

    def latest_job(self, video_id: str) -> dict | None:
        with self.connect() as c:
            row = c.execute(
                "SELECT * FROM jobs WHERE video_id = ? ORDER BY created_at DESC, rowid DESC LIMIT 1",
                (video_id,),
            ).fetchone()
        return job_row(row)

    def active_job(self, video_id: str) -> dict | None:
        with self.connect() as c:
            row = c.execute(
                "SELECT * FROM jobs WHERE video_id = ? AND status IN ('queued', 'running') LIMIT 1",
                (video_id,),
            ).fetchone()
        return job_row(row)

    def claim_next_job(self, worker_id: str, lease_s: float = LEASE_S, max_attempts: int = MAX_ATTEMPTS) -> dict | None:
        """Atomically give `worker_id` the oldest queued job, or a running job whose holder's lease has expired (its
        worker died), with a fresh lease. Jobs that already lost `max_attempts` workers fail instead. Several worker
        processes may call this at once: SQLite runs one write transaction at a time, so a job goes to one worker."""
        t = now()
        with self.connect() as c:
            c.execute(
                "UPDATE jobs SET status = 'failed', error = 'worker lost ' || attempts || ' times', worker_id = NULL, "
                "lease_until = NULL, updated_at = ? "
                "WHERE status = 'running' AND (lease_until IS NULL OR lease_until < ?) AND attempts >= ?",
                (t, t, max_attempts),
            )
            row = c.execute(
                "UPDATE jobs SET status = 'running', worker_id = ?, lease_until = ?, attempts = attempts + 1, "
                "updated_at = ? WHERE id = ("
                "  SELECT id FROM jobs WHERE status = 'queued' "
                "  OR (status = 'running' AND (lease_until IS NULL OR lease_until < ?)) "
                "  ORDER BY created_at, rowid LIMIT 1"
                ") RETURNING *",
                (worker_id, now(lease_s), t, t),
            ).fetchone()
        return job_row(row)

    def renew_lease(self, jid: str, worker_id: str, lease_s: float = LEASE_S) -> bool:
        """Extend the holder's lease; False when the job is no longer this worker's (it was taken after the lease
        ran out, or it finished)."""
        with self.connect() as c:
            n = c.execute(
                "UPDATE jobs SET lease_until = ? WHERE id = ? AND worker_id = ? AND status = 'running'",
                (now(lease_s), jid, worker_id),
            ).rowcount
        return n > 0

    def release_job(self, jid: str, worker_id: str) -> bool:
        """Queue the job again at once (a worker told to stop); the interrupted run does not count as an attempt."""
        with self.connect() as c:
            n = c.execute(
                "UPDATE jobs SET status = 'queued', worker_id = NULL, lease_until = NULL, stage = NULL, "
                "attempts = MAX(attempts - 1, 0), updated_at = ? WHERE id = ? AND worker_id = ? AND status = 'running'",
                (now(), jid, worker_id),
            ).rowcount
        return n > 0

    def update_job(self, jid: str, worker_id: str | None = None, **fields) -> bool:
        """Set job fields. With `worker_id`, only while that worker holds the job (False otherwise), so a worker that
        lost its lease cannot overwrite the new holder's state. Finishing a job drops its lease."""
        fields["updated_at"] = now()
        if fields.get("status") in FINISHED:
            fields.update(worker_id=None, lease_until=None)
        if isinstance(fields.get("timings"), dict):
            fields["timings"] = json.dumps(fields["timings"])
        cols = ", ".join(f"{k} = ?" for k in fields)
        where, args = "id = ?", [jid]
        if worker_id is not None:
            where, args = "id = ? AND worker_id = ?", [jid, worker_id]
        with self.connect() as c:
            n = c.execute(f"UPDATE jobs SET {cols} WHERE {where}", (*fields.values(), *args)).rowcount
        return n > 0

    # rallies
    def replace_rallies(self, video_id: str, rallies: list[dict]) -> None:
        cols = ("idx", "start_s", "end_s", "winner", "reason", "confidence", "landing_x", "landing_y", "source")
        with self.connect() as c:
            c.execute("DELETE FROM rallies WHERE video_id = ?", (video_id,))
            c.executemany(
                f"INSERT INTO rallies (video_id, {', '.join(cols)}) VALUES (?{', ?' * len(cols)})",
                [(video_id, *(r.get(k) for k in cols)) for r in rallies],
            )

    def replace_detected_rallies(self, video_id: str, found: list[dict], min_iou: float = 0.5) -> None:
        """Detected rallies (start_s, end_s, confidence) replace the video's rallies; a user's winner correction moves
        to the new rally that overlaps its old one (temporal IoU >= min_iou), so a rerun keeps it."""
        old = self.list_rallies(video_id)

        def iou(a, b):
            inter = max(0.0, min(a[1], b[1]) - max(a[0], b[0]))
            union = max(a[1], b[1]) - min(a[0], b[0])
            return inter / union if union > 0 else 0.0

        rows = [
            {
                "idx": k,
                "start_s": r["start_s"],
                "end_s": r["end_s"],
                "winner": None,
                "reason": None,
                "confidence": r.get("confidence"),
                "landing_x": None,
                "landing_y": None,
                "source": "model",
            }
            for k, r in enumerate(found)
        ]
        self.replace_rallies(video_id, rows)
        for o in old:
            if not o.get("winner_override"):
                continue
            best = max(rows, key=lambda r: iou((o["start_s"], o["end_s"]), (r["start_s"], r["end_s"])), default=None)
            if best and iou((o["start_s"], o["end_s"]), (best["start_s"], best["end_s"])) >= min_iou:
                self.set_rally_override(video_id, best["idx"], o["winner_override"])

    def list_rallies(self, video_id: str) -> list[dict]:
        with self.connect() as c:
            rows = c.execute("SELECT * FROM rallies WHERE video_id = ? ORDER BY idx", (video_id,)).fetchall()
        return [dict(r) for r in rows]

    def set_rally_override(self, video_id: str, idx: int, winner: str | None) -> bool:
        with self.connect() as c:
            n = c.execute(
                "UPDATE rallies SET winner_override = ? WHERE video_id = ? AND idx = ?",
                (winner, video_id, idx),
            ).rowcount
        return n > 0

    # rosters
    def get_roster(self, video_id: str) -> list[dict]:
        with self.connect() as c:
            rows = c.execute(
                "SELECT team, number, name FROM rosters WHERE video_id = ? ORDER BY team, number", (video_id,)
            ).fetchall()
        return [dict(r) for r in rows]

    def replace_roster(self, video_id: str, players: list[dict]) -> None:
        with self.connect() as c:
            c.execute("DELETE FROM rosters WHERE video_id = ?", (video_id,))
            c.executemany(
                "INSERT INTO rosters (video_id, team, number, name) VALUES (?, ?, ?, ?)",
                [(video_id, p["team"], p["number"], p.get("name")) for p in players],
            )

    def ensure_on_roster(self, video_id: str, team: str, number: int) -> None:
        with self.connect() as c:
            c.execute(
                "INSERT OR IGNORE INTO rosters (video_id, team, number) VALUES (?, ?, ?)", (video_id, team, number)
            )

    # tags
    def add_tag(self, video_id: str, time_s: float, kind: str, team: str, number: int, outcome: str | None) -> dict:
        tag = {
            "id": uuid.uuid4().hex[:12],
            "video_id": video_id,
            "time_s": time_s,
            "kind": kind,
            "team": team,
            "number": number,
            "outcome": outcome,
            "created_at": now(),
        }
        with self.connect() as c:
            c.execute(
                "INSERT INTO tags (id, video_id, time_s, kind, team, number, outcome, created_at) "
                "VALUES (:id, :video_id, :time_s, :kind, :team, :number, :outcome, :created_at)",
                tag,
            )
        return tag

    def list_tags(self, video_id: str) -> list[dict]:
        with self.connect() as c:
            rows = c.execute("SELECT * FROM tags WHERE video_id = ? ORDER BY time_s, id", (video_id,)).fetchall()
        return [dict(r) for r in rows]

    def get_tag(self, video_id: str, tag_id: str) -> dict | None:
        with self.connect() as c:
            row = c.execute("SELECT * FROM tags WHERE video_id = ? AND id = ?", (video_id, tag_id)).fetchone()
        return dict(row) if row else None

    def update_tag(self, video_id: str, tag_id: str, **fields) -> None:
        cols = ", ".join(f"{k} = ?" for k in fields)
        with self.connect() as c:
            c.execute(f"UPDATE tags SET {cols} WHERE video_id = ? AND id = ?", (*fields.values(), video_id, tag_id))

    def delete_tag(self, video_id: str, tag_id: str) -> bool:
        with self.connect() as c:
            return c.execute("DELETE FROM tags WHERE video_id = ? AND id = ?", (video_id, tag_id)).rowcount > 0

    def dismiss_suggestion(self, video_id: str, suggestion_id: str) -> None:
        with self.connect() as c:
            c.execute("INSERT OR IGNORE INTO dismissed_suggestions VALUES (?, ?)", (video_id, suggestion_id))

    def dismissed_suggestions(self, video_id: str) -> set[str]:
        with self.connect() as c:
            rows = c.execute("SELECT suggestion_id FROM dismissed_suggestions WHERE video_id = ?", (video_id,))
            return {r[0] for r in rows}

    # court corrections (overlaid on court.json when read: vball.court_registration.apply_corrections)
    def court_corrections(self, video_id: str) -> list[dict]:
        with self.connect() as c:
            rows = c.execute(
                "SELECT shot, frame, points_px, ids FROM court_corrections WHERE video_id = ? ORDER BY shot",
                (video_id,),
            )
            return [
                {
                    "shot": r["shot"],
                    "frame": r["frame"],
                    "points_px": json.loads(r["points_px"]),
                    "ids": json.loads(r["ids"]),
                }
                for r in rows
            ]

    def set_court_correction(self, video_id: str, shot: int, frame: int, points_px: list, ids: list[int]) -> None:
        with self.connect() as c:
            c.execute(
                "INSERT OR REPLACE INTO court_corrections VALUES (?, ?, ?, ?, ?, ?)",
                (video_id, shot, frame, json.dumps(points_px), json.dumps(ids), now()),
            )

    def clear_court_correction(self, video_id: str, shot: int) -> bool:
        with self.connect() as c:
            return (
                c.execute("DELETE FROM court_corrections WHERE video_id = ? AND shot = ?", (video_id, shot)).rowcount
                > 0
            )
