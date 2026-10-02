from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from pompom_lab.database import Database


class DatabaseTests(unittest.TestCase):
    def test_migrations_are_repeatable(self) -> None:
        root = Path(__file__).resolve().parent.parent
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "lab.sqlite3"
            Database(path, root / "migrations")
            Database(path, root / "migrations")
            self.assertTrue(path.exists())

    def test_rescue_tables_exist(self) -> None:
        root = Path(__file__).resolve().parent.parent
        with tempfile.TemporaryDirectory() as temp:
            database = Database(Path(temp) / "lab.sqlite3", root / "migrations")
            with database.connect() as connection:
                tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            self.assertIn("rescue_runs", tables)
            self.assertIn("rescue_reviews", tables)


if __name__ == "__main__":
    unittest.main()
