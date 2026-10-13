"""Rolling backups of the app database (change back-up-app-database).

The database holds the only copy of what the user enters (court corrections, tags, rosters, winner corrections);
analysis results are files and can be recomputed. Backups use SQLite's online backup, which is consistent while the
API and the worker are running.

  python -m vball_app.backup --list
  python -m vball_app.backup --restore webapp-20261013T120400Z.db    # backs up the current database first
"""

import argparse
import logging
import sqlite3
from contextlib import closing
from datetime import UTC, datetime, timedelta
from pathlib import Path

from .settings import DATA, DB_PATH

BACKUPS = DATA / "backups"
KEEP = 10
EVERY = timedelta(hours=1)  # at most one backup per hour after finished jobs
log = logging.getLogger(__name__)


def _stamp(path: Path) -> datetime:
    return datetime.strptime(path.stem.removeprefix("webapp-"), "%Y%m%dT%H%M%S%fZ").replace(tzinfo=UTC)


def _copy(src: Path, dest: Path) -> None:
    """SQLite online backup of one database file into another (consistent while others write)."""
    with closing(sqlite3.connect(src)) as a, closing(sqlite3.connect(dest)) as b:
        a.backup(b)


def backups(folder: Path = BACKUPS) -> list[Path]:
    """Backup files, oldest first."""
    return sorted(folder.glob("webapp-*.db"))


def back_up(db: Path = DB_PATH, folder: Path = BACKUPS, keep: int = KEEP) -> Path | None:
    """Copy the database to a new timestamped file and remove all but the newest `keep`. None without a database."""
    if not db.exists():
        return None
    folder.mkdir(parents=True, exist_ok=True)
    dest = folder / f"webapp-{datetime.now(UTC):%Y%m%dT%H%M%S%fZ}.db"
    _copy(db, dest)
    for old in backups(folder)[:-keep]:
        old.unlink()
    log.info("database backed up to %s", dest.name)
    return dest


def back_up_if_due(db: Path = DB_PATH, folder: Path = BACKUPS, every: timedelta = EVERY) -> Path | None:
    """A backup unless the newest one is younger than `every`."""
    existing = backups(folder)
    if existing and datetime.now(UTC) - _stamp(existing[-1]) < every:
        return None
    return back_up(db, folder)


def restore(backup: Path, db: Path = DB_PATH, folder: Path = BACKUPS) -> Path | None:
    """Replace the database with a backup; the current database is backed up first (returned)."""
    if not backup.exists():
        raise FileNotFoundError(backup)
    saved = back_up(db, folder, keep=KEEP + 1)  # never prune the file being restored in the same call
    _copy(backup, db)
    log.info("database restored from %s", backup.name)
    return saved


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    group = ap.add_mutually_exclusive_group(required=True)
    group.add_argument("--list", action="store_true", help="list backups, oldest first")
    group.add_argument("--restore", metavar="FILE", help="a file name from --list")
    args = ap.parse_args()
    if args.list:
        for b in backups():
            print(f"{b.name}  {b.stat().st_size // 1024} KB")
        return
    saved = restore(BACKUPS / Path(args.restore).name)
    print(f"restored {args.restore}; the previous database is {saved.name if saved else 'not saved (none existed)'}")


if __name__ == "__main__":
    main()
