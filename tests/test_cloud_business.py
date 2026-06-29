from dataclasses import replace
from datetime import date, datetime
import unittest
from zoneinfo import ZoneInfo

from tapinshift.classifier import RuleBasedClassifier
from tapinshift.cloud.business import CloudEventFactory, CloudSlackService, has_same_day_punch, rounding_setting_item
from tapinshift.cloud.events import CloudEventType, SyncStatus, event_to_item
from tapinshift.cloud.sync import InMemoryCloudEventStore
from tapinshift.config import RoundingConfig
from tapinshift.models import PunchType


class CloudEventFactoryTest(unittest.TestCase):
    def test_punch_event_fixes_tapped_and_reflected_times(self) -> None:
        factory = CloudEventFactory(
            rounding=RoundingConfig(
                mode="30m",
                direction="nearest",
                clock_in_direction="ceil",
                clock_out_direction="floor",
            ),
            classifier=RuleBasedClassifier(),
        )
        tapped_at = datetime(2026, 6, 27, 8, 10, tzinfo=ZoneInfo("Asia/Tokyo"))

        event = factory.punch_event(
            slack_user_id="U123",
            punch_type=PunchType.CLOCK_IN,
            tapped_at=tapped_at,
            event_id="evt-in",
        )

        self.assertEqual(event.event_type, CloudEventType.PUNCH)
        self.assertEqual(event.sync_status, SyncStatus.QUEUED)
        self.assertEqual(event.tapped_at, tapped_at)
        self.assertEqual(event.reflected_at, datetime(2026, 6, 27, 8, 30, tzinfo=ZoneInfo("Asia/Tokyo")))
        self.assertEqual(event.rounding_mode, "30m")
        self.assertEqual(event.rounding_direction, "ceil")

    def test_punch_event_uses_clock_out_floor_direction(self) -> None:
        factory = CloudEventFactory(
            rounding=RoundingConfig(
                mode="30m",
                direction="nearest",
                clock_in_direction="ceil",
                clock_out_direction="floor",
            ),
            classifier=RuleBasedClassifier(),
        )

        event = factory.punch_event(
            slack_user_id="U123",
            punch_type=PunchType.CLOCK_OUT,
            tapped_at=datetime(2026, 6, 27, 18, 10, tzinfo=ZoneInfo("Asia/Tokyo")),
            event_id="evt-out",
        )

        self.assertEqual(event.reflected_at, datetime(2026, 6, 27, 18, 0, tzinfo=ZoneInfo("Asia/Tokyo")))
        self.assertEqual(event.rounding_direction, "floor")

    def test_note_reflection_event_stores_classification_at_acceptance_time(self) -> None:
        factory = CloudEventFactory(
            rounding=RoundingConfig(mode="none", direction="nearest"),
            classifier=RuleBasedClassifier(),
        )
        accepted_at = datetime(2026, 6, 27, 9, 0, tzinfo=ZoneInfo("Asia/Tokyo"))

        event = factory.note_reflection_event(
            slack_user_id="U123",
            target_date=date(2026, 6, 27),
            raw_note="アレア品川、南平⇔市ヶ谷、1134",
            accepted_at=accepted_at,
            event_id="evt-note",
        )

        self.assertEqual(event.event_type, CloudEventType.NOTE_REFLECTION)
        self.assertEqual(event.created_at, accepted_at)
        self.assertEqual(event.classification.notice, "アレア品川")  # type: ignore[union-attr]
        self.assertEqual(event.classification.expense_item, "南平⇔市ヶ谷")  # type: ignore[union-attr]
        self.assertEqual(event.classification.amount, 1134)  # type: ignore[union-attr]
        self.assertFalse(event.classification.needs_confirmation)  # type: ignore[union-attr]

    def test_empty_note_reflection_event_is_failed(self) -> None:
        factory = CloudEventFactory(
            rounding=RoundingConfig(mode="none", direction="nearest"),
            classifier=RuleBasedClassifier(),
        )

        event = factory.note_reflection_event(
            slack_user_id="U123",
            target_date=date(2026, 6, 27),
            raw_note="  ",
            accepted_at=datetime(2026, 6, 27, 9, 0, tzinfo=ZoneInfo("Asia/Tokyo")),
            event_id="evt-note",
        )

        self.assertEqual(event.sync_status, SyncStatus.FAILED)
        self.assertEqual(event.error, "No note was provided.")
        self.assertFalse(event.retryable)

    def test_day_edit_event_keeps_blank_fields_as_none(self) -> None:
        factory = CloudEventFactory(
            rounding=RoundingConfig(mode="none", direction="nearest"),
            classifier=RuleBasedClassifier(),
        )

        event = factory.day_edit_event(
            slack_user_id="U123",
            target_date=date(2026, 6, 27),
            accepted_at=datetime(2026, 6, 27, 10, 0, tzinfo=ZoneInfo("Asia/Tokyo")),
            values={
                "clock_in": "09:00",
                "clock_out": "",
                "notice": "アレア品川",
                "expense_item": " ",
                "amount": "1,134円",
            },
            event_id="evt-edit",
        )

        self.assertEqual(event.event_type, CloudEventType.DAY_EDIT)
        self.assertEqual(event.clock_in, "09:00")
        self.assertIsNone(event.clock_out)
        self.assertEqual(event.notice, "アレア品川")
        self.assertIsNone(event.expense_item)
        self.assertEqual(event.amount, 1134)

    def test_day_edit_event_with_invalid_amount_is_failed(self) -> None:
        factory = CloudEventFactory(
            rounding=RoundingConfig(mode="none", direction="nearest"),
            classifier=RuleBasedClassifier(),
        )

        event = factory.day_edit_event(
            slack_user_id="U123",
            target_date=date(2026, 6, 27),
            accepted_at=datetime(2026, 6, 27, 10, 0, tzinfo=ZoneInfo("Asia/Tokyo")),
            values={
                "clock_in": "09:00",
                "clock_out": "18:00",
                "notice": "アレア品川",
                "expense_item": "南平⇔市ヶ谷",
                "amount": "abc",
            },
            event_id="evt-edit",
        )

        self.assertEqual(event.sync_status, SyncStatus.FAILED)
        self.assertIsNone(event.amount)
        self.assertFalse(event.retryable)
        self.assertIn("invalid literal", event.error or "")

    def test_rounding_setting_item_rejects_unsupported_mode(self) -> None:
        with self.assertRaises(ValueError):
            rounding_setting_item("U123", "7m", datetime(2026, 6, 27, 10, 0, tzinfo=ZoneInfo("Asia/Tokyo")))

    def test_rounding_setting_item_can_be_saved_to_single_table(self) -> None:
        item = rounding_setting_item(
            "U123",
            "30m",
            datetime(2026, 6, 27, 10, 0, tzinfo=ZoneInfo("Asia/Tokyo")),
        )

        self.assertEqual(item["PK"], "USER#U123")
        self.assertEqual(item["SK"], "SETTING#time_rounding.mode")
        self.assertEqual(item["value"], "30m")

    def test_event_to_item_uses_business_event_fields(self) -> None:
        factory = CloudEventFactory(
            rounding=RoundingConfig(mode="15m", direction="nearest", clock_in_direction="ceil"),
            classifier=RuleBasedClassifier(),
        )
        event = factory.punch_event(
            slack_user_id="U123",
            punch_type=PunchType.CLOCK_IN,
            tapped_at=datetime(2026, 6, 27, 8, 1, tzinfo=ZoneInfo("Asia/Tokyo")),
            event_id="evt-in",
        )

        item = event_to_item(event)

        self.assertEqual(item["sync_status"], "queued")
        self.assertEqual(item["rounding_mode"], "15m")
        self.assertEqual(item["rounding_direction"], "ceil")

    def test_has_same_day_punch_detects_active_duplicate(self) -> None:
        factory = CloudEventFactory(
            rounding=RoundingConfig(mode="none", direction="nearest"),
            classifier=RuleBasedClassifier(),
        )
        existing = factory.punch_event(
            slack_user_id="U123",
            punch_type=PunchType.CLOCK_IN,
            tapped_at=datetime(2026, 6, 27, 8, 0, tzinfo=ZoneInfo("Asia/Tokyo")),
            event_id="evt-existing",
        )

        self.assertTrue(
            has_same_day_punch(
                [existing],
                target_date=date(2026, 6, 27),
                punch_type=PunchType.CLOCK_IN,
            )
        )

    def test_has_same_day_punch_ignores_failed_duplicate(self) -> None:
        failed = CloudEventFactory(
            rounding=RoundingConfig(mode="none", direction="nearest"),
            classifier=RuleBasedClassifier(),
        ).punch_event(
            slack_user_id="U123",
            punch_type=PunchType.CLOCK_IN,
            tapped_at=datetime(2026, 6, 27, 8, 0, tzinfo=ZoneInfo("Asia/Tokyo")),
            event_id="evt-failed",
        )
        failed = replace(failed, sync_status=SyncStatus.FAILED)

        self.assertFalse(
            has_same_day_punch(
                [failed],
                target_date=date(2026, 6, 27),
                punch_type=PunchType.CLOCK_IN,
            )
        )

    def test_cloud_slack_service_saves_punch_event(self) -> None:
        store = InMemoryCloudEventStore()
        service = CloudSlackService(
            store=store,
            factory=CloudEventFactory(
                rounding=RoundingConfig(mode="15m", direction="nearest", clock_in_direction="ceil"),
                classifier=RuleBasedClassifier(),
            ),
        )

        event = service.record_punch(
            slack_user_id="U123",
            punch_type=PunchType.CLOCK_IN,
            accepted_at=datetime(2026, 6, 27, 8, 1, tzinfo=ZoneInfo("Asia/Tokyo")),
        )

        self.assertEqual(store.get(event.event_id), event)
        self.assertEqual(event.reflected_at, datetime(2026, 6, 27, 8, 15, tzinfo=ZoneInfo("Asia/Tokyo")))

    def test_cloud_slack_service_marks_duplicate_punch_warning(self) -> None:
        store = InMemoryCloudEventStore()
        service = CloudSlackService(
            store=store,
            factory=CloudEventFactory(
                rounding=RoundingConfig(mode="none", direction="nearest"),
                classifier=RuleBasedClassifier(),
            ),
        )
        service.record_punch(
            slack_user_id="U123",
            punch_type=PunchType.CLOCK_IN,
            accepted_at=datetime(2026, 6, 27, 8, 0, tzinfo=ZoneInfo("Asia/Tokyo")),
        )

        duplicate = service.record_punch(
            slack_user_id="U123",
            punch_type=PunchType.CLOCK_IN,
            accepted_at=datetime(2026, 6, 27, 8, 5, tzinfo=ZoneInfo("Asia/Tokyo")),
        )

        self.assertTrue(duplicate.duplicate_warning)


if __name__ == "__main__":
    unittest.main()
