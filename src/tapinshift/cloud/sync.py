from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta
from typing import Protocol

from .events import CloudEvent, SyncStatus


DEFAULT_CLAIM_TIMEOUT = timedelta(minutes=10)


class CloudEventStore(Protocol):
    def list_for_claim(self, *, now: datetime, claim_timeout: timedelta, limit: int) -> list[CloudEvent]:
        raise NotImplementedError

    def claim_event(
        self,
        event: CloudEvent,
        *,
        claim_token: str,
        now: datetime,
        claim_timeout: timedelta,
    ) -> CloudEvent | None:
        raise NotImplementedError

    def mark_reflected(self, *, event_id: str, claim_token: str, now: datetime) -> CloudEvent:
        raise NotImplementedError

    def mark_failed(self, *, event_id: str, claim_token: str, error: str, retryable: bool, now: datetime) -> CloudEvent:
        raise NotImplementedError

    def save(self, event: CloudEvent) -> None:
        raise NotImplementedError

    def get(self, event_id: str) -> CloudEvent | None:
        raise NotImplementedError

    def list_user_events(self, slack_user_id: str) -> list[CloudEvent]:
        raise NotImplementedError

    def get_setting(self, slack_user_id: str, key: str) -> str | None:
        raise NotImplementedError

    def set_setting(self, slack_user_id: str, key: str, value: str, updated_at: datetime) -> None:
        raise NotImplementedError


class CloudSyncService:
    def __init__(self, store: CloudEventStore, *, claim_timeout: timedelta = DEFAULT_CLAIM_TIMEOUT) -> None:
        self.store = store
        self.claim_timeout = claim_timeout

    def claim(self, *, claim_token: str, now: datetime, limit: int = 10) -> list[CloudEvent]:
        if not claim_token.strip():
            raise ValueError("claim_token is required")
        normalized_limit = max(1, min(limit, 100))
        candidates = self.store.list_for_claim(now=now, claim_timeout=self.claim_timeout, limit=normalized_limit)
        claimed = []
        for event in candidates:
            updated = self.store.claim_event(
                event,
                claim_token=claim_token,
                now=now,
                claim_timeout=self.claim_timeout,
            )
            if updated is not None:
                claimed.append(updated)
        return claimed

    def mark_reflected(self, *, event_id: str, claim_token: str, now: datetime) -> CloudEvent:
        if not claim_token.strip():
            raise ValueError("claim_token is required")
        return self.store.mark_reflected(event_id=event_id, claim_token=claim_token, now=now)

    def mark_failed(self, *, event_id: str, claim_token: str, error: str, retryable: bool, now: datetime) -> CloudEvent:
        if not claim_token.strip():
            raise ValueError("claim_token is required")
        return self.store.mark_failed(
            event_id=event_id,
            claim_token=claim_token,
            error=error,
            retryable=retryable,
            now=now,
        )


class InMemoryCloudEventStore:
    def __init__(self, events: list[CloudEvent] | None = None) -> None:
        self._events: dict[str, CloudEvent] = {}
        self._settings: dict[tuple[str, str], str] = {}
        for event in events or []:
            self.save(event)

    def list_for_claim(self, *, now: datetime, claim_timeout: timedelta, limit: int) -> list[CloudEvent]:
        stale_before = now - claim_timeout
        candidates = [
            event
            for event in self._events.values()
            if event.sync_status == SyncStatus.QUEUED
            or (
                event.sync_status == SyncStatus.CLAIMED
                and event.claimed_at is not None
                and event.claimed_at <= stale_before
            )
        ]
        candidates.sort(key=lambda event: event.created_at)
        return candidates[:limit]

    def save(self, event: CloudEvent) -> None:
        self._events[event.event_id] = event

    def claim_event(
        self,
        event: CloudEvent,
        *,
        claim_token: str,
        now: datetime,
        claim_timeout: timedelta,
    ) -> CloudEvent | None:
        current = self._events.get(event.event_id)
        if current is None:
            return None
        stale_before = now - claim_timeout
        claimable = current.sync_status == SyncStatus.QUEUED or (
            current.sync_status == SyncStatus.CLAIMED
            and current.claimed_at is not None
            and current.claimed_at <= stale_before
        )
        if not claimable:
            return None
        updated = replace(
            current,
            sync_status=SyncStatus.CLAIMED,
            claim_token=claim_token,
            claimed_at=now,
            updated_at=now,
            error=None,
        )
        self.save(updated)
        return updated

    def mark_reflected(self, *, event_id: str, claim_token: str, now: datetime) -> CloudEvent:
        event = self._claimed_by(event_id, claim_token)
        updated = replace(event, sync_status=SyncStatus.REFLECTED, updated_at=now, retryable=None, error=None)
        self.save(updated)
        return updated

    def mark_failed(self, *, event_id: str, claim_token: str, error: str, retryable: bool, now: datetime) -> CloudEvent:
        event = self._claimed_by(event_id, claim_token)
        updated = replace(
            event,
            sync_status=SyncStatus.FAILED,
            updated_at=now,
            retryable=retryable,
            error=error,
        )
        self.save(updated)
        return updated

    def get(self, event_id: str) -> CloudEvent | None:
        return self._events.get(event_id)

    def list_user_events(self, slack_user_id: str) -> list[CloudEvent]:
        return sorted(
            [event for event in self._events.values() if event.slack_user_id == slack_user_id],
            key=lambda event: event.created_at,
        )

    def get_setting(self, slack_user_id: str, key: str) -> str | None:
        return self._settings.get((slack_user_id, key))

    def set_setting(self, slack_user_id: str, key: str, value: str, updated_at: datetime) -> None:  # noqa: ARG002
        self._settings[(slack_user_id, key)] = value

    def _claimed_by(self, event_id: str, claim_token: str) -> CloudEvent:
        event = self.get(event_id)
        if event is None:
            raise KeyError(f"Cloud event not found: {event_id}")
        if event.sync_status != SyncStatus.CLAIMED or event.claim_token != claim_token:
            raise ValueError(f"Cloud event is not claimed by this agent: {event_id}")
        return event
