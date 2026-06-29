from datetime import date, datetime, timezone
import unittest

from tapinshift.cloud.events import CloudEvent, CloudEventType, SyncStatus, event_to_item, item_to_event, setting_item
from tapinshift.models import Classification, PunchType


class CloudEventItemTest(unittest.TestCase):
    def test_punch_event_to_dynamodb_item_includes_sync_index_keys(self) -> None:
        created_at = datetime(2026, 6, 27, 8, 10, tzinfo=timezone.utc)
        event = CloudEvent(
            event_id="evt-1",
            slack_user_id="U123",
            event_type=CloudEventType.PUNCH,
            target_date=date(2026, 6, 27),
            sync_status=SyncStatus.QUEUED,
            created_at=created_at,
            updated_at=created_at,
            punch_type=PunchType.CLOCK_IN,
            tapped_at=created_at,
            reflected_at=datetime(2026, 6, 27, 8, 30, tzinfo=timezone.utc),
            rounding_mode="30m",
            rounding_direction="ceil",
        )

        item = event_to_item(event)

        self.assertEqual(item["PK"], "USER#U123")
        self.assertEqual(item["SK"], "EVENT#2026-06-27#2026-06-27T08:10:00+00:00#evt-1")
        self.assertEqual(item["GSI1PK"], "SYNC#queued")
        self.assertEqual(item["GSI1SK"], "2026-06-27T08:10:00+00:00")
        self.assertEqual(item["punch_type"], "clock_in")
        self.assertEqual(item["reflected_at"], "2026-06-27T08:30:00+00:00")

    def test_note_event_to_dynamodb_item_includes_classification_result(self) -> None:
        now = datetime(2026, 6, 27, 9, 0, tzinfo=timezone.utc)
        event = CloudEvent(
            event_id="evt-2",
            slack_user_id="U123",
            event_type=CloudEventType.NOTE_REFLECTION,
            target_date=date(2026, 6, 27),
            sync_status=SyncStatus.QUEUED,
            created_at=now,
            updated_at=now,
            raw_note="アレア品川、南平⇔市ヶ谷、1134",
            classification=Classification(
                notice="アレア品川",
                expense_item="南平⇔市ヶ谷",
                amount=1134,
                confidence=0.9,
                needs_confirmation=False,
            ),
        )

        item = event_to_item(event)

        self.assertEqual(item["raw_note"], "アレア品川、南平⇔市ヶ谷、1134")
        self.assertEqual(item["notice"], "アレア品川")
        self.assertEqual(item["expense_item"], "南平⇔市ヶ谷")
        self.assertEqual(item["amount"], 1134)
        self.assertFalse(item["needs_confirmation"])

    def test_setting_item_uses_user_setting_sort_key(self) -> None:
        updated_at = datetime(2026, 6, 27, 10, 0, tzinfo=timezone.utc)

        item = setting_item("U123", "time_rounding.mode", "30m", updated_at)

        self.assertEqual(item["PK"], "USER#U123")
        self.assertEqual(item["SK"], "SETTING#time_rounding.mode")
        self.assertEqual(item["value"], "30m")

    def test_item_to_event_restores_punch_event(self) -> None:
        created_at = datetime(2026, 6, 27, 8, 10, tzinfo=timezone.utc)
        original = CloudEvent(
            event_id="evt-1",
            slack_user_id="U123",
            event_type=CloudEventType.PUNCH,
            target_date=date(2026, 6, 27),
            sync_status=SyncStatus.CLAIMED,
            created_at=created_at,
            updated_at=created_at,
            punch_type=PunchType.CLOCK_IN,
            tapped_at=created_at,
            reflected_at=created_at,
            rounding_mode="30m",
            rounding_direction="ceil",
            claim_token="agent-1",
            claimed_at=created_at,
        )

        restored = item_to_event(event_to_item(original))

        self.assertEqual(restored.event_id, original.event_id)
        self.assertEqual(restored.sync_status, SyncStatus.CLAIMED)
        self.assertEqual(restored.punch_type, PunchType.CLOCK_IN)
        self.assertEqual(restored.claim_token, "agent-1")


if __name__ == "__main__":
    unittest.main()
