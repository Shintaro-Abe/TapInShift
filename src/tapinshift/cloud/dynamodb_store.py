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

    def claim_event(
        self,
        event: CloudEvent,
        *,
        claim_token: str,
        now: datetime,
        claim_timeout: timedelta,
    ) -> CloudEvent | None:
        stale_before = now - claim_timeout
        try:
            response = self.table.update_item(
                Key={"PK": event.pk, "SK": event.sk},
                UpdateExpression=(
                    "SET sync_status = :claimed, GSI1PK = :gsi, claim_token = :token, "
                    "claimed_at = :now, updated_at = :now REMOVE #err, retryable"
                ),
                ConditionExpression=(
                    "sync_status = :queued OR "
                    "(sync_status = :claimed AND attribute_exists(claimed_at) AND claimed_at <= :stale_before)"
                ),
                ExpressionAttributeNames={"#err": "error"},
                ExpressionAttributeValues={
                    ":queued": SyncStatus.QUEUED.value,
                    ":claimed": SyncStatus.CLAIMED.value,
                    ":gsi": f"SYNC#{SyncStatus.CLAIMED.value}",
                    ":token": claim_token,
                    ":now": now.isoformat(),
                    ":stale_before": stale_before.isoformat(),
                },
                ReturnValues="ALL_NEW",
            )
        except Exception as exc:  # noqa: BLE001 - boto3 is optional in tests.
            if _is_conditional_check_failed(exc):
                return None
            raise
        return item_to_event(response["Attributes"])

    def mark_reflected(self, *, event_id: str, claim_token: str, now: datetime) -> CloudEvent:
        event = self._get_existing(event_id)
        try:
            response = self.table.update_item(
                Key={"PK": event.pk, "SK": event.sk},
                UpdateExpression=(
                    "SET sync_status = :reflected, GSI1PK = :gsi, updated_at = :now "
                    "REMOVE #err, retryable, claim_token, claimed_at"
                ),
                ConditionExpression="sync_status = :claimed AND claim_token = :token",
                ExpressionAttributeNames={"#err": "error"},
                ExpressionAttributeValues={
                    ":claimed": SyncStatus.CLAIMED.value,
                    ":reflected": SyncStatus.REFLECTED.value,
                    ":gsi": f"SYNC#{SyncStatus.REFLECTED.value}",
                    ":token": claim_token,
                    ":now": now.isoformat(),
                },
                ReturnValues="ALL_NEW",
            )
        except Exception as exc:  # noqa: BLE001 - boto3 is optional in tests.
            if _is_conditional_check_failed(exc):
                raise ValueError(f"Cloud event is not claimed by this agent: {event_id}") from exc
            raise
        return item_to_event(response["Attributes"])

    def mark_failed(self, *, event_id: str, claim_token: str, error: str, retryable: bool, now: datetime) -> CloudEvent:
        event = self._get_existing(event_id)
        try:
            response = self.table.update_item(
                Key={"PK": event.pk, "SK": event.sk},
                UpdateExpression=(
                    "SET sync_status = :failed, GSI1PK = :gsi, updated_at = :now, "
                    "retryable = :retryable, #err = :error REMOVE claim_token, claimed_at"
                ),
                ConditionExpression="sync_status = :claimed AND claim_token = :token",
                ExpressionAttributeNames={"#err": "error"},
                ExpressionAttributeValues={
                    ":claimed": SyncStatus.CLAIMED.value,
                    ":failed": SyncStatus.FAILED.value,
                    ":gsi": f"SYNC#{SyncStatus.FAILED.value}",
                    ":token": claim_token,
                    ":now": now.isoformat(),
                    ":retryable": retryable,
                    ":error": error,
                },
                ReturnValues="ALL_NEW",
            )
        except Exception as exc:  # noqa: BLE001 - boto3 is optional in tests.
            if _is_conditional_check_failed(exc):
                raise ValueError(f"Cloud event is not claimed by this agent: {event_id}") from exc
            raise
        return item_to_event(response["Attributes"])

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

    def _get_existing(self, event_id: str) -> CloudEvent:
        event = self.get(event_id)
        if event is None:
            raise KeyError(f"Cloud event not found: {event_id}")
        return event


def _is_conditional_check_failed(exc: Exception) -> bool:
    response = getattr(exc, "response", {})
    error = response.get("Error", {}) if isinstance(response, dict) else {}
    return error.get("Code") == "ConditionalCheckFailedException"


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
