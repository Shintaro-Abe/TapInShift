from __future__ import annotations

import sqlite3
import tempfile
import unittest
from contextlib import closing
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from tapinshift.config import (
    AppConfig,
    CloudSyncConfig,
    ExcelColumns,
    ExcelConfig,
    ExcelDefaults,
    RoundingConfig,
    SlackConfig,
)
from tapinshift.models import Classification, PunchType, ReflectionStatus
from tapinshift.service import PunchService
from tapinshift.storage import EventStore


class FakeClassifier:
    def __init__(self, classification: Classification) -> None:
        self.classification = classification
        self.calls: list[str] = []

    def classify(self, note: str) -> Classification:
        self.calls.append(note)
        return self.classification


class FakeWriter:
    def __init__(self, write_error: Exception | None = None) -> None:
        self.write_calls = []
        self.update_calls = []
        self.write_error = write_error

    def write_punch(self, **kwargs):
        self.write_calls.append(kwargs)
        if self.write_error:
            raise self.write_error
        return type("Result", (), {"reflected_at": kwargs["reflected_time"], "row": 7})()

    def update_day(self, **kwargs):
        self.update_calls.append(kwargs)
        return type("Result", (), {"reflected_at": datetime(2026, 6, 21, 9, 0), "row": 7})()


class PunchServiceTest(unittest.TestCase):
    def test_handle_punch_reflects_and_persists_event(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = EventStore(Path(tmp) / "tapinshift.sqlite3")
            store.initialize()
            writer = FakeWriter()
            classifier = FakeClassifier(Classification(None, "新宿駅-渋谷駅", 320, 0.9, False))
            service = PunchService(
                config=_config(Path(tmp)),
                store=store,
                classifier=classifier,
                writer=writer,
            )

            event = service.handle_punch(
                slack_event_id="evt-1",
                slack_user_id="U123",
                punch_type=PunchType.CLOCK_IN,
                tapped_at=datetime(2026, 6, 21, 9, 8, tzinfo=ZoneInfo("Asia/Tokyo")),
            )

            self.assertEqual(event.status, ReflectionStatus.REFLECTED)
            self.assertEqual(len(writer.write_calls), 1)
            self.assertEqual(writer.write_calls[0]["target_date"], date(2026, 6, 21))
            self.assertIsNone(writer.write_calls[0]["classification"])
            self.assertEqual(classifier.calls, [])
            stored_event = store.get_day_events("2026-06-21")[0]
            self.assertEqual(stored_event.note, "")
            self.assertIsNone(stored_event.classification)

    def test_handle_punch_does_not_classify_notes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = EventStore(Path(tmp) / "tapinshift.sqlite3")
            store.initialize()
            writer = FakeWriter()
            classifier = FakeClassifier(Classification(None, None, None, 0.2, True))
            service = PunchService(
                config=_config(Path(tmp)),
                store=store,
                classifier=classifier,
                writer=writer,
            )

            event = service.handle_punch(
                slack_event_id="evt-1",
                slack_user_id="U123",
                punch_type=PunchType.CLOCK_OUT,
                tapped_at=datetime(2026, 6, 21, 18, 0, tzinfo=ZoneInfo("Asia/Tokyo")),
            )

            self.assertEqual(event.status, ReflectionStatus.REFLECTED)
            self.assertEqual(len(writer.write_calls), 1)
            self.assertIsNone(writer.write_calls[0]["classification"])
            self.assertEqual(classifier.calls, [])
            stored_event = store.get_day_events("2026-06-21")[0]
            self.assertEqual(stored_event.status, ReflectionStatus.REFLECTED)
            self.assertIsNone(stored_event.classification)
            self.assertIsNone(stored_event.error)

    def test_handle_punch_records_writer_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = EventStore(Path(tmp) / "tapinshift.sqlite3")
            store.initialize()
            writer = FakeWriter(write_error=ValueError("Cell already has a value: F13"))
            service = PunchService(
                config=_config(Path(tmp)),
                store=store,
                classifier=FakeClassifier(Classification(None, None, None, 1.0, False)),
                writer=writer,
            )

            event = service.handle_punch(
                slack_event_id="evt-1",
                slack_user_id="U123",
                punch_type=PunchType.CLOCK_IN,
                tapped_at=datetime(2026, 6, 21, 9, 0, tzinfo=ZoneInfo("Asia/Tokyo")),
            )

            self.assertEqual(event.status, ReflectionStatus.FAILED)
            self.assertEqual(event.error, "Cell already has a value: F13")
            stored_event = store.get_day_events("2026-06-21")[0]
            self.assertEqual(stored_event.status, ReflectionStatus.FAILED)
            self.assertEqual(stored_event.error, "Cell already has a value: F13")

    def test_handle_punch_uses_per_punch_rounding_direction(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = EventStore(Path(tmp) / "tapinshift.sqlite3")
            store.initialize()
            writer = FakeWriter()
            service = PunchService(
                config=_config(
                    Path(tmp),
                    rounding=RoundingConfig(
                        mode="15m",
                        direction="nearest",
                        clock_in_direction="ceil",
                        clock_out_direction="floor",
                    ),
                ),
                store=store,
                classifier=FakeClassifier(Classification(None, None, None, 1.0, False)),
                writer=writer,
            )

            service.handle_punch(
                slack_event_id="evt-in",
                slack_user_id="U123",
                punch_type=PunchType.CLOCK_IN,
                tapped_at=datetime(2026, 6, 21, 9, 1, tzinfo=ZoneInfo("Asia/Tokyo")),
            )
            service.handle_punch(
                slack_event_id="evt-out",
                slack_user_id="U123",
                punch_type=PunchType.CLOCK_OUT,
                tapped_at=datetime(2026, 6, 21, 18, 14, tzinfo=ZoneInfo("Asia/Tokyo")),
            )

            self.assertEqual(
                writer.write_calls[0]["reflected_time"],
                datetime(2026, 6, 21, 9, 15, tzinfo=ZoneInfo("Asia/Tokyo")),
            )
            self.assertEqual(
                writer.write_calls[1]["reflected_time"],
                datetime(2026, 6, 21, 18, 0, tzinfo=ZoneInfo("Asia/Tokyo")),
            )

    def test_handle_punch_uses_rounding_mode_saved_from_ui(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = EventStore(Path(tmp) / "tapinshift.sqlite3")
            store.initialize()
            writer = FakeWriter()
            service = PunchService(
                config=_config(
                    Path(tmp),
                    rounding=RoundingConfig(mode="none", direction="nearest", clock_in_direction="ceil"),
                ),
                store=store,
                classifier=FakeClassifier(Classification(None, None, None, 1.0, False)),
                writer=writer,
            )

            service.update_rounding_mode("15m")
            service.handle_punch(
                slack_event_id="evt-in",
                slack_user_id="U123",
                punch_type=PunchType.CLOCK_IN,
                tapped_at=datetime(2026, 6, 21, 9, 1, tzinfo=ZoneInfo("Asia/Tokyo")),
            )

            self.assertEqual(service.current_rounding_mode(), "15m")
            self.assertEqual(
                writer.write_calls[0]["reflected_time"],
                datetime(2026, 6, 21, 9, 15, tzinfo=ZoneInfo("Asia/Tokyo")),
            )

    def test_update_rounding_mode_rejects_unsupported_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = EventStore(Path(tmp) / "tapinshift.sqlite3")
            store.initialize()
            service = PunchService(
                config=_config(Path(tmp)),
                store=store,
                classifier=FakeClassifier(Classification(None, None, None, 1.0, False)),
                writer=FakeWriter(),
            )

            with self.assertRaises(ValueError):
                service.update_rounding_mode("7m")

    def test_update_day_records_failed_validation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "tapinshift.sqlite3"
            store = EventStore(db_path)
            store.initialize()
            service = PunchService(
                config=_config(Path(tmp)),
                store=store,
                classifier=FakeClassifier(Classification(None, None, None, 1.0, False)),
                writer=FakeWriter(),
            )

            status = service.update_day(
                slack_user_id="U123",
                target_date="2026-06-21",
                values={"clock_in": "09:00", "clock_out": "", "notice": "", "expense_item": "", "amount": "abc"},
            )

            self.assertEqual(status, ReflectionStatus.FAILED)
            with closing(sqlite3.connect(db_path)) as conn:
                row = conn.execute("SELECT status, error, amount FROM manual_edits").fetchone()
            self.assertEqual(row[0], ReflectionStatus.FAILED.value)
            self.assertIn("invalid literal", row[1])
            self.assertEqual(row[2], "abc")

    def test_update_day_accepts_comma_and_yen_amount(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "tapinshift.sqlite3"
            store = EventStore(db_path)
            store.initialize()
            writer = FakeWriter()
            service = PunchService(
                config=_config(Path(tmp)),
                store=store,
                classifier=FakeClassifier(Classification(None, None, None, 1.0, False)),
                writer=writer,
            )

            status = service.update_day(
                slack_user_id="U123",
                target_date="2026-06-21",
                values={"clock_in": "", "clock_out": "", "notice": "", "expense_item": "新宿駅-渋谷駅", "amount": "1,200円"},
            )

            self.assertEqual(status, ReflectionStatus.REFLECTED)
            self.assertEqual(writer.update_calls[0]["amount"], 1200)
            with closing(sqlite3.connect(db_path)) as conn:
                row = conn.execute("SELECT status, amount FROM manual_edits").fetchone()
            self.assertEqual(row[0], ReflectionStatus.REFLECTED.value)
            self.assertEqual(row[1], 1200)

    def test_apply_note_to_day_updates_classified_fields_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "tapinshift.sqlite3"
            store = EventStore(db_path)
            store.initialize()
            writer = FakeWriter()
            service = PunchService(
                config=_config(Path(tmp)),
                store=store,
                classifier=FakeClassifier(Classification("渋谷オフィス", "新宿駅-渋谷駅", 320, 0.9, False)),
                writer=writer,
            )

            status, error = service.apply_note_to_day(
                slack_user_id="U123",
                target_date="2026-06-21",
                note="渋谷オフィス 新宿駅-渋谷駅 320円",
            )

            self.assertEqual(status, ReflectionStatus.REFLECTED)
            self.assertIsNone(error)
            self.assertEqual(writer.update_calls[0]["clock_in"], None)
            self.assertEqual(writer.update_calls[0]["clock_out"], None)
            self.assertEqual(writer.update_calls[0]["notice"], "渋谷オフィス")
            self.assertEqual(writer.update_calls[0]["expense_item"], "新宿駅-渋谷駅")
            self.assertEqual(writer.update_calls[0]["amount"], 320)
            with closing(sqlite3.connect(db_path)) as conn:
                row = conn.execute("SELECT status, notice, expense_item, amount FROM manual_edits").fetchone()
            self.assertEqual(row[0], ReflectionStatus.REFLECTED.value)
            self.assertEqual(row[1], "渋谷オフィス")
            self.assertEqual(row[2], "新宿駅-渋谷駅")
            self.assertEqual(row[3], 320)

    def test_apply_note_to_day_records_empty_note_as_failed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "tapinshift.sqlite3"
            store = EventStore(db_path)
            store.initialize()
            writer = FakeWriter()
            service = PunchService(
                config=_config(Path(tmp)),
                store=store,
                classifier=FakeClassifier(Classification(None, None, None, 1.0, False)),
                writer=writer,
            )

            status, error = service.apply_note_to_day(slack_user_id="U123", target_date="2026-06-21", note="")

            self.assertEqual(status, ReflectionStatus.FAILED)
            self.assertEqual(error, "No note was provided.")
            self.assertEqual(writer.update_calls, [])


def _config(base: Path, rounding: RoundingConfig | None = None) -> AppConfig:
    return AppConfig(
        timezone=ZoneInfo("Asia/Tokyo"),
        database_path=base / "tapinshift.sqlite3",
        excel=ExcelConfig(
            path=base / "timesheet.xlsx",
            sheet_name="6",
            password_env="TAPINSHIFT_EXCEL_PASSWORD",
            columns=ExcelColumns(
                table="B",
                attendance="C",
                late="D",
                early="E",
                date="L",
                clock_in="F",
                clock_out="G",
                notice="W",
                expense_item="Y",
                amount="AB",
            ),
            first_data_row=7,
            last_data_row=37,
            date_format="%Y-%m-%d",
            defaults=ExcelDefaults(table=1, attendance=1, late=0, early=0),
        ),
        time_rounding=rounding or RoundingConfig(mode="none", direction="nearest"),
        slack=SlackConfig(bot_token_env="SLACK_BOT_TOKEN", app_token_env="SLACK_APP_TOKEN"),
        cloud_sync=CloudSyncConfig(
            endpoint="https://example.lambda-url.aws/",
            endpoint_env="TAPINSHIFT_CLOUD_ENDPOINT",
            token_env="TAPINSHIFT_SYNC_TOKEN",
            poll_interval_seconds=300,
            claim_limit=10,
        ),
    )


if __name__ == "__main__":
    unittest.main()
