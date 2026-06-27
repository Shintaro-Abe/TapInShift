from __future__ import annotations

import io
import json
import sqlite3
import tempfile
import unittest
from argparse import Namespace
from contextlib import closing, redirect_stdout
from pathlib import Path

from scripts.timesheet_tools import cmd_show_db


class TimesheetToolsTest(unittest.TestCase):
    def test_show_db_handles_database_without_app_settings_table(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config_path = _write_config(Path(tmp))
            _create_legacy_db(Path(tmp) / "tapinshift.sqlite3")

            output = io.StringIO()
            with redirect_stdout(output):
                exit_code = cmd_show_db(Namespace(config=str(config_path), limit=1))

        self.assertEqual(exit_code, 0)
        self.assertIn("# app_settings", output.getvalue())
        self.assertIn("app_settings table does not exist yet", output.getvalue())

    def test_show_db_prints_app_settings(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config_path = _write_config(Path(tmp))
            db_path = Path(tmp) / "tapinshift.sqlite3"
            _create_legacy_db(db_path)
            with closing(sqlite3.connect(db_path)) as conn:
                conn.execute("CREATE TABLE app_settings (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
                conn.execute("INSERT INTO app_settings (key, value) VALUES (?, ?)", ("time_rounding.mode", "30m"))
                conn.commit()

            output = io.StringIO()
            with redirect_stdout(output):
                exit_code = cmd_show_db(Namespace(config=str(config_path), limit=1))

        self.assertEqual(exit_code, 0)
        self.assertIn("('time_rounding.mode', '30m')", output.getvalue())

    def test_show_db_hides_non_displayable_app_settings(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config_path = _write_config(Path(tmp))
            db_path = Path(tmp) / "tapinshift.sqlite3"
            _create_legacy_db(db_path)
            with closing(sqlite3.connect(db_path)) as conn:
                conn.execute("CREATE TABLE app_settings (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
                conn.execute("INSERT INTO app_settings (key, value) VALUES (?, ?)", ("time_rounding.mode", "30m"))
                conn.execute("INSERT INTO app_settings (key, value) VALUES (?, ?)", ("excel.password", "secret"))
                conn.commit()

            output = io.StringIO()
            with redirect_stdout(output):
                exit_code = cmd_show_db(Namespace(config=str(config_path), limit=1))

        self.assertEqual(exit_code, 0)
        text = output.getvalue()
        self.assertIn("('time_rounding.mode', '30m')", text)
        self.assertNotIn("excel.password", text)
        self.assertNotIn("secret", text)


def _write_config(base: Path) -> Path:
    config_path = base / "config.json"
    config_path.write_text(json.dumps({"database_path": "tapinshift.sqlite3"}), encoding="utf-8")
    return config_path


def _create_legacy_db(db_path: Path) -> None:
    with closing(sqlite3.connect(db_path)) as conn:
        conn.execute(
            """
            CREATE TABLE punch_events (
                tapped_at TEXT,
                punch_type TEXT,
                status TEXT,
                error TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE manual_edits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT,
                target_date TEXT,
                status TEXT,
                error TEXT
            )
            """
        )
        conn.commit()


if __name__ == "__main__":
    unittest.main()
