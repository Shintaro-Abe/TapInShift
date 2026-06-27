from datetime import datetime
import tempfile
import unittest
from zoneinfo import ZoneInfo

from tapinshift.models import Classification, PunchEvent, PunchType, ReflectionStatus
from tapinshift.storage import EventStore


class EventStoreTest(unittest.TestCase):
    def test_store_round_trips_setting(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            from pathlib import Path

            store = EventStore(Path(tmp) / "tapinshift.sqlite3")
            store.initialize()

            store.set_setting("time_rounding.mode", "15m")
            store.set_setting("time_rounding.mode", "30m")

            self.assertEqual(store.get_setting("time_rounding.mode"), "30m")

    def test_event_store_round_trips_event(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            from pathlib import Path

            store = EventStore(Path(tmp) / "tapinshift.sqlite3")
            store.initialize()
            event = PunchEvent(
                slack_event_id="evt-1",
                slack_user_id="U123",
                punch_type=PunchType.CLOCK_IN,
                tapped_at=datetime(2026, 6, 21, 9, 0, tzinfo=ZoneInfo("Asia/Tokyo")),
                reflected_at=None,
                note="渋谷オフィス 新宿駅-渋谷駅 320円",
                classification=Classification("渋谷オフィス", "新宿駅-渋谷駅", 320, 0.9, False),
                status=ReflectionStatus.PENDING,
            )

            store.upsert_event(event)

            events = store.get_day_events("2026-06-21")
            self.assertEqual(len(events), 1)
            self.assertEqual(events[0].slack_event_id, "evt-1")
            self.assertIsNotNone(events[0].classification)
            self.assertEqual(events[0].classification.amount, 320)


if __name__ == "__main__":
    unittest.main()
