from datetime import datetime
import unittest
from zoneinfo import ZoneInfo

from tapinshift.time_rounding import round_time


class TimeRoundingTest(unittest.TestCase):
    def test_round_time_none_keeps_original_timestamp(self) -> None:
        value = datetime(2026, 6, 21, 9, 7, 10, tzinfo=ZoneInfo("Asia/Tokyo"))

        self.assertEqual(round_time(value, "none"), value)

    def test_round_time_nearest_15_minutes(self) -> None:
        value = datetime(2026, 6, 21, 9, 8, tzinfo=ZoneInfo("Asia/Tokyo"))

        self.assertEqual(
            round_time(value, "15m", "nearest"),
            datetime(2026, 6, 21, 9, 15, tzinfo=ZoneInfo("Asia/Tokyo")),
        )

    def test_round_time_floor_30_minutes(self) -> None:
        value = datetime(2026, 6, 21, 9, 44, tzinfo=ZoneInfo("Asia/Tokyo"))

        self.assertEqual(
            round_time(value, "30m", "floor"),
            datetime(2026, 6, 21, 9, 30, tzinfo=ZoneInfo("Asia/Tokyo")),
        )

    def test_round_time_ceil_15_minutes(self) -> None:
        value = datetime(2026, 6, 21, 9, 1, tzinfo=ZoneInfo("Asia/Tokyo"))

        self.assertEqual(
            round_time(value, "15m", "ceil"),
            datetime(2026, 6, 21, 9, 15, tzinfo=ZoneInfo("Asia/Tokyo")),
        )

    def test_round_time_rejects_unsupported_mode(self) -> None:
        value = datetime(2026, 6, 21, 9, 44, tzinfo=ZoneInfo("Asia/Tokyo"))

        with self.assertRaises(ValueError):
            round_time(value, "7m", "nearest")


if __name__ == "__main__":
    unittest.main()
