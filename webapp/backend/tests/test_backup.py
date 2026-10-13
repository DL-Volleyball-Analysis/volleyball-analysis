import sqlite3
from datetime import timedelta

import pytest
from vball_app import backup


def make_db(path, rows):
    with sqlite3.connect(path) as c:
        c.execute("CREATE TABLE IF NOT EXISTS t (x)")
        c.execute("DELETE FROM t")
        c.executemany("INSERT INTO t VALUES (?)", [(r,) for r in rows])
    return path


def rows(path):
    with sqlite3.connect(path) as c:
        return [r[0] for r in c.execute("SELECT x FROM t ORDER BY x")]


def test_backup_keeps_rows_and_only_the_newest_files(tmp_path):
    db, folder = make_db(tmp_path / "app.db", [1, 2]), tmp_path / "backups"
    made = [backup.back_up(db, folder, keep=3) for _ in range(5)]
    assert rows(made[-1]) == [1, 2]
    assert backup.backups(folder) == made[-3:]
    assert backup.back_up(tmp_path / "missing.db", folder) is None


def test_backup_if_due_waits_an_hour(tmp_path):
    db, folder = make_db(tmp_path / "app.db", [1]), tmp_path / "backups"
    assert backup.back_up_if_due(db, folder) is not None
    assert backup.back_up_if_due(db, folder) is None  # newest is seconds old
    assert backup.back_up_if_due(db, folder, every=timedelta(0)) is not None


def test_restore_brings_rows_back_and_saves_the_current_database(tmp_path):
    db, folder = make_db(tmp_path / "app.db", [1, 2, 3]), tmp_path / "backups"
    good = backup.back_up(db, folder)
    make_db(db, [])  # emptied, as on 2026-10-13
    saved = backup.restore(good, db, folder)
    assert rows(db) == [1, 2, 3] and rows(saved) == []
    with pytest.raises(FileNotFoundError):
        backup.restore(folder / "nope.db", db, folder)


def test_backups_stay_in_the_test_data_folder():
    from vball_app import settings

    assert backup.BACKUPS.parent == settings.DATA
