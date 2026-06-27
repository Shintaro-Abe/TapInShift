from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tapinshift.config import load_config


class ConfigTest(unittest.TestCase):
    def test_load_config_reads_per_punch_rounding_directions(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "config.json"
            config_path.write_text(
                json.dumps(
                    {
                        "timezone": "Asia/Tokyo",
                        "database_path": "tapinshift.sqlite3",
                        "excel": {
                            "path": "timesheet.xlsx",
                            "sheet_name": "6",
                            "columns": {
                                "clock_in": "F",
                                "clock_out": "G",
                                "date": "L",
                                "notice": "W",
                                "expense_item": "Y",
                                "amount": "AB",
                            },
                        },
                        "time_rounding": {
                            "mode": "15m",
                            "direction": "nearest",
                            "clock_in_direction": "ceil",
                            "clock_out_direction": "floor",
                        },
                    }
                ),
                encoding="utf-8",
            )

            config = load_config(config_path)

        self.assertEqual(config.time_rounding.mode, "15m")
        self.assertEqual(config.time_rounding.direction_for("clock_in"), "ceil")
        self.assertEqual(config.time_rounding.direction_for("clock_out"), "floor")


if __name__ == "__main__":
    unittest.main()
