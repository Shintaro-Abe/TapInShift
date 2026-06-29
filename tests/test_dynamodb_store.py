from datetime import date, datetime, timedelta, timezone
import unittest

from tapinshift.cloud.dynamodb_store import DynamoDBCloudEventStore
from tapinshift.cloud.events import CloudEvent, CloudEventType, SyncStatus, event_to_item


class DynamoDBCloudEventStoreTest(unittest.TestCase):
    def test_save_and_list_for_claim_reads_queued_events(self) -> None:
        now = datetime(2026, 6, 27, 9, 0, tzinfo=timezone.utc)
        table = FakeTable()
        store = DynamoDBCloudEventStore(table)
        event = _event("evt-1", now)

        store.save(event)
        claimed = store.list_for_claim(now=now, claim_timeout=timedelta(minutes=10), limit=10)

        self.assertEqual([item.event_id for item in claimed], ["evt-1"])

    def test_list_for_claim_includes_stale_claimed_events(self) -> None:
        now = datetime(2026, 6, 27, 9, 0, tzinfo=timezone.utc)
        stale = _event(
            "evt-1",
            now - timedelta(minutes=30),
            sync_status=SyncStatus.CLAIMED,
            claimed_at=now - timedelta(minutes=11),
        )
        store = DynamoDBCloudEventStore(FakeTable([event_to_item(stale)]))

        events = store.list_for_claim(now=now, claim_timeout=timedelta(minutes=10), limit=10)

        self.assertEqual([event.event_id for event in events], ["evt-1"])

    def test_claim_event_updates_only_claimable_event(self) -> None:
        now = datetime(2026, 6, 27, 9, 0, tzinfo=timezone.utc)
        event = _event("evt-1", now)
        table = FakeTable([event_to_item(event)])
        store = DynamoDBCloudEventStore(table)

        claimed = store.claim_event(
            event,
            claim_token="agent-1",
            now=now,
            claim_timeout=timedelta(minutes=10),
        )
        second = store.claim_event(
            event,
            claim_token="agent-2",
            now=now,
            claim_timeout=timedelta(minutes=10),
        )

        self.assertIsNotNone(claimed)
        self.assertEqual(claimed.claim_token, "agent-1")  # type: ignore[union-attr]
        self.assertIsNone(second)

    def test_mark_reflected_requires_matching_claim_token(self) -> None:
        now = datetime(2026, 6, 27, 9, 0, tzinfo=timezone.utc)
        event = _event("evt-1", now)
        table = FakeTable([event_to_item(event)])
        store = DynamoDBCloudEventStore(table)
        store.claim_event(event, claim_token="agent-1", now=now, claim_timeout=timedelta(minutes=10))

        with self.assertRaises(ValueError):
            store.mark_reflected(event_id="evt-1", claim_token="agent-2", now=now)

        reflected = store.mark_reflected(event_id="evt-1", claim_token="agent-1", now=now)

        self.assertEqual(reflected.sync_status, SyncStatus.REFLECTED)

    def test_settings_round_trip(self) -> None:
        now = datetime(2026, 6, 27, 9, 0, tzinfo=timezone.utc)
        store = DynamoDBCloudEventStore(FakeTable())

        store.set_setting("U123", "time_rounding.mode", "30m", now)

        self.assertEqual(store.get_setting("U123", "time_rounding.mode"), "30m")

    def test_list_user_events(self) -> None:
        now = datetime(2026, 6, 27, 9, 0, tzinfo=timezone.utc)
        table = FakeTable([event_to_item(_event("evt-1", now))])
        store = DynamoDBCloudEventStore(table)

        events = store.list_user_events("U123")

        self.assertEqual([event.event_id for event in events], ["evt-1"])


class FakeTable:
    def __init__(self, items=None) -> None:
        self.items = list(items or [])

    def put_item(self, *, Item):
        self.items = [item for item in self.items if not (item["PK"] == Item["PK"] and item["SK"] == Item["SK"])]
        self.items.append(Item)

    def get_item(self, *, Key):
        for item in self.items:
            if item["PK"] == Key["PK"] and item["SK"] == Key["SK"]:
                return {"Item": item}
        return {}

    def query(self, **kwargs):
        values = kwargs["ExpressionAttributeValues"]
        if "IndexName" in kwargs:
            return {"Items": [item for item in self.items if item.get("GSI1PK") == values[":pk"]]}
        return {
            "Items": [
                item
                for item in self.items
                if item["PK"] == values[":pk"] and str(item["SK"]).startswith(values[":prefix"])
            ]
        }

    def update_item(self, **kwargs):
        key = kwargs["Key"]
        item = self.get_item(Key=key).get("Item")
        if item is None:
            raise FakeConditionalCheckFailed()
        values = kwargs["ExpressionAttributeValues"]
        expression = kwargs["UpdateExpression"]
        if ":token" in values:
            if "claim_token = :token" in kwargs["ConditionExpression"]:
                if item.get("sync_status") != values[":claimed"] or item.get("claim_token") != values[":token"]:
                    raise FakeConditionalCheckFailed()
            else:
                if item.get("sync_status") == values[":queued"]:
                    pass
                elif item.get("sync_status") == values[":claimed"] and item.get("claimed_at") <= values[":stale_before"]:
                    pass
                else:
                    raise FakeConditionalCheckFailed()
        if ":gsi" in values:
            item["GSI1PK"] = values[":gsi"]
        if ":claimed" in values and values.get(":gsi") == "SYNC#claimed":
            item["sync_status"] = values[":claimed"]
        if ":reflected" in values:
            item["sync_status"] = values[":reflected"]
        if ":failed" in values:
            item["sync_status"] = values[":failed"]
        if ":token" in values and "claim_token = :token" not in kwargs.get("ConditionExpression", ""):
            item["claim_token"] = values[":token"]
        if ":now" in values:
            item["updated_at"] = values[":now"]
            if "claimed_at = :now" in expression:
                item["claimed_at"] = values[":now"]
        if ":retryable" in values:
            item["retryable"] = values[":retryable"]
        if ":error" in values:
            item["error"] = values[":error"]
        for key_to_remove in ("error", "retryable", "claim_token", "claimed_at"):
            if key_to_remove in expression.split("REMOVE", 1)[-1]:
                item.pop(key_to_remove, None)
        return {"Attributes": item}


class FakeConditionalCheckFailed(Exception):
    response = {"Error": {"Code": "ConditionalCheckFailedException"}}


def _event(
    event_id: str,
    created_at: datetime,
    *,
    sync_status: SyncStatus = SyncStatus.QUEUED,
    claimed_at: datetime | None = None,
) -> CloudEvent:
    return CloudEvent(
        event_id=event_id,
        slack_user_id="U123",
        event_type=CloudEventType.PUNCH,
        target_date=date(2026, 6, 27),
        sync_status=sync_status,
        created_at=created_at,
        updated_at=created_at,
        claimed_at=claimed_at,
    )


if __name__ == "__main__":
    unittest.main()
