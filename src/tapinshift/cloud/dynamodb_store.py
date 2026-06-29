from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from .events import CloudEvent, SyncStatus, event_to_item, item_to_event, setting_item


class DynamoDBCloudEventStore:
    def __init__(self, table: Any) -> None:
        self.table = table

    @classmethod
    def from_table_name(cls, table_name: str) -> "DynamoDBCloudEventStore":
        try:
            import boto3
        except ImportError as exc:
            raise RuntimeError("boto3 package is required for DynamoDB cloud sync") from exc
        return cls(boto3.resource("dynamodb").Table(table_name))

    def list_for_claim(self, *, now: datetime, claim_timeout: timedelta, limit: int) -> list[CloudEvent]:
        stale_before = now - claim_timeout
        queued = self._query_sync_status(SyncStatus.QUEUED, limit)
        stale_claimed = [
            event
            for event in self._query_sync_status(SyncStatus.CLAIMED, limit)
            if event.claimed_at is not None and event.claimed_at <= stale_before
        ]
        events = queued + stale_claimed
        events.sort(key=lambda event: event.created_at)
        return events[:limit]

    def save(self, event: CloudEvent) -> None:
        self.table.put_item(Item=event_to_item(event))

    def get(self, event_id: str) -> CloudEvent | None:
        for status in SyncStatus:
            for event in self._query_sync_status(status, 100):
                if event.event_id == event_id:
                    return event
        return None

    def list_user_events(self, slack_user_id: str) -> list[CloudEvent]:
        key_condition = _key("PK").eq(f"USER#{slack_user_id}") & _key("SK").begins_with("EVENT#")
        kwargs = {"KeyConditionExpression": key_condition}
        if isinstance(key_condition, _FakeKey):
            kwargs["ExpressionAttributeValues"] = {":pk": f"USER#{slack_user_id}", ":prefix": "EVENT#"}
        response = self.table.query(**kwargs)
        return sorted([item_to_event(item) for item in response.get("Items", [])], key=lambda event: event.created_at)

    def get_setting(self, slack_user_id: str, key: str) -> str | None:
        response = self.table.get_item(Key={"PK": f"USER#{slack_user_id}", "SK": f"SETTING#{key}"})
        item = response.get("Item")
        return str(item["value"]) if item else None

    def set_setting(self, slack_user_id: str, key: str, value: str, updated_at: datetime) -> None:
        self.table.put_item(Item=setting_item(slack_user_id, key, value, updated_at))

    def _query_sync_status(self, status: SyncStatus, limit: int) -> list[CloudEvent]:
        key_condition = _key("GSI1PK").eq(f"SYNC#{status.value}")
        kwargs = {"IndexName": "GSI1", "KeyConditionExpression": key_condition, "Limit": limit}
        if isinstance(key_condition, _FakeKey):
            kwargs["ExpressionAttributeValues"] = {":pk": f"SYNC#{status.value}"}
        response = self.table.query(**kwargs)
        return [item_to_event(item) for item in response.get("Items", [])]


def _key(name: str):
    try:
        from boto3.dynamodb.conditions import Key
    except ImportError:
        return _FakeKey(name)
    return Key(name)


class _FakeKey:
    def __init__(self, name: str) -> None:
        self.name = name

    def eq(self, value: str):
        return self

    def begins_with(self, value: str):
        return self

    def __and__(self, other):
        return self
