"""SQLite storage: videos, analysis jobs and rallies.

The API and the worker are separate processes, so the job queue lives here (WAL mode) instead
of in API memory. Rallies keep the model's winner and the user's correction side by side; the
corrections double as labels for measuring scoring accuracy.
"""
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
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
    updated_at TEXT NOT NULL
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
"""

FINISHED = ("done", "failed")


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class Database:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as c:
            c.execute("PRAGMA journal_mode=WAL")
            c.executescript(SCHEMA)

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
                (vid, name, path, meta.get("fps"), meta.get("frames"), meta.get("width"),
                 meta.get("height"), now()),
            )
        return self.get_video(vid)

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
        return self.get_job(jid)

    def get_job(self, jid: str) -> dict | None:
        with self.connect() as c:
            row = c.execute("SELECT * FROM jobs WHERE id = ?", (jid,)).fetchone()
        return dict(row) if row else None

    def latest_job(self, video_id: str) -> dict | None:
        with self.connect() as c:
            row = c.execute(
                "SELECT * FROM jobs WHERE video_id = ? ORDER BY created_at DESC, rowid DESC LIMIT 1",
                (video_id,),
            ).fetchone()
        return dict(row) if row else None

    def active_job(self, video_id: str) -> dict | None:
        with self.connect() as c:
            row = c.execute(
                "SELECT * FROM jobs WHERE video_id = ? AND status IN ('queued', 'running') LIMIT 1",
                (video_id,),
            ).fetchone()
        return dict(row) if row else None

    def claim_next_job(self) -> dict | None:
        """Atomically move the oldest queued job to running."""
        with self.connect() as c:
            row = c.execute(
                "UPDATE jobs SET status = 'running', updated_at = ? WHERE id = ("
                "  SELECT id FROM jobs WHERE status = 'queued' ORDER BY created_at, rowid LIMIT 1"
                ") RETURNING *",
                (now(),),
            ).fetchone()
        return dict(row) if row else None

    def update_job(self, jid: str, **fields) -> None:
        fields["updated_at"] = now()
        cols = ", ".join(f"{k} = ?" for k in fields)
        with self.connect() as c:
            c.execute(f"UPDATE jobs SET {cols} WHERE id = ?", (*fields.values(), jid))

    def requeue_running(self) -> int:
        """After a worker crash/restart, jobs left 'running' are queued again."""
        with self.connect() as c:
            return c.execute(
                "UPDATE jobs SET status = 'queued', updated_at = ? WHERE status = 'running'", (now(),)
            ).rowcount

    # rallies
    def replace_rallies(self, video_id: str, rallies: list[dict]) -> None:
        cols = ("idx", "start_s", "end_s", "winner", "reason", "confidence",
                "landing_x", "landing_y", "source")
        with self.connect() as c:
            c.execute("DELETE FROM rallies WHERE video_id = ?", (video_id,))
            c.executemany(
                f"INSERT INTO rallies (video_id, {', '.join(cols)}) VALUES (?{', ?' * len(cols)})",
                [(video_id, *(r.get(k) for k in cols)) for r in rallies],
            )

    def list_rallies(self, video_id: str) -> list[dict]:
        with self.connect() as c:
            rows = c.execute(
                "SELECT * FROM rallies WHERE video_id = ? ORDER BY idx", (video_id,)
            ).fetchall()
        return [dict(r) for r in rows]

    def set_rally_override(self, video_id: str, idx: int, winner: str | None) -> bool:
        with self.connect() as c:
            n = c.execute(
                "UPDATE rallies SET winner_override = ? WHERE video_id = ? AND idx = ?",
                (winner, video_id, idx),
            ).rowcount
        return n > 0
