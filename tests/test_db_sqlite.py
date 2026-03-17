from __future__ import annotations

from sqlalchemy import text

from pipeliner.config import Settings
from pipeliner.db import Database


def test_sqlite_connection_enables_wal_and_busy_timeout(tmp_path) -> None:
    settings = Settings(data_dir=tmp_path / ".pipeliner")
    settings.ensure_directories()
    db = Database(settings)
    try:
        with db.engine.connect() as connection:
            journal_mode = connection.execute(text("PRAGMA journal_mode")).scalar_one()
            busy_timeout = connection.execute(text("PRAGMA busy_timeout")).scalar_one()
            foreign_keys = connection.execute(text("PRAGMA foreign_keys")).scalar_one()

        assert str(journal_mode).lower() == "wal"
        assert int(busy_timeout) == 30000
        assert int(foreign_keys) == 1
    finally:
        db.dispose()
