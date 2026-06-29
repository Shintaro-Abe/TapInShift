from __future__ import annotations

from datetime import datetime
from typing import Protocol

from tapinshift.excel_writer import ExcelTimesheetWriter
from tapinshift.models import Classification, PunchEvent, ReflectionStatus
from tapinshift.storage import EventStore

from .events import CloudEvent, CloudEventType


class CloudSyncClient(Protocol):
    def claim(self, *, claim_token: str, now: datetime, limit: int) -> list[CloudEvent]:
        raise NotImplementedError

    def mark_reflected(self, *, event_id: str, claim_token: str, now: datetime) -> None:
        raise NotImplementedError

    def mark_failed(self, *, event_id: str, claim_token: str, error: str, retryable: bool, now: datetime) -> None:
        raise NotImplementedError


class CloudExcelSynchronizer:
    def __init__(
        self,
        *,
        client: CloudSyncClient,
        writer: ExcelTimesheetWriter,
        store: EventStore,
        claim_token: str,
        claim_limit: int,
    ) -> None:
        self.client = client
        self.writer = writer
        self.store = store
        self.claim_token = claim_token
        self.claim_limit = claim_limit

    def sync_once(self, *, now: datetime) -> int:
        events = self.client.claim(claim_token=self.claim_token, now=now, limit=self.claim_limit)
        for event in events:
            try:
                self._reflect_event(event)
            except Exception as exc:  # noqa: BLE001 - reported to cloud and local audit log.
                error = str(exc)
                self._record_failure(event, error)
                self.client.mark_failed(
                    event_id=event.event_id,
                    claim_token=self.claim_token,
                    error=error,
                    retryable=_is_retryable_error(error),
                    now=now,
                )
            else:
                self.client.mark_reflected(event_id=event.event_id, claim_token=self.claim_token, now=now)
        return len(events)

    def _reflect_event(self, event: CloudEvent) -> None:
        if event.event_type == CloudEventType.PUNCH:
            self._reflect_punch(event)
            return
        if event.event_type == CloudEventType.NOTE_REFLECTION:
            self._reflect_note(event)
            return
        if event.event_type == CloudEventType.DAY_EDIT:
            self._reflect_day_edit(event)
            return
        raise ValueError(f"Unsupported cloud event type: {event.event_type}")

    def _reflect_punch(self, event: CloudEvent) -> None:
        if event.punch_type is None or event.tapped_at is None or event.reflected_at is None:
            raise ValueError("Cloud punch event is missing required fields")
        result = self.writer.write_punch(
            target_date=event.target_date,
            punch_type=event.punch_type,
            reflected_time=event.reflected_at,
            classification=None,
        )
        self.store.upsert_event(
            PunchEvent(
                slack_event_id=event.event_id,
                slack_user_id=event.slack_user_id,
                punch_type=event.punch_type,
                tapped_at=event.tapped_at,
                reflected_at=result.reflected_at,
                note="",
                classification=None,
                status=ReflectionStatus.REFLECTED,
            )
        )

    def _reflect_note(self, event: CloudEvent) -> None:
        values = _classification_values(event.classification)
        if event.classification and event.classification.needs_confirmation:
            self.store.record_manual_edit(
                slack_user_id=event.slack_user_id,
                target_date=event.target_date.isoformat(),
                values=values,
                status=ReflectionStatus.NEEDS_CONFIRMATION,
                error="Note classification needs confirmation.",
            )
            return
        self.writer.update_day(target_date=event.target_date, **values)
        self.store.record_manual_edit(
            slack_user_id=event.slack_user_id,
            target_date=event.target_date.isoformat(),
            values=values,
            status=ReflectionStatus.REFLECTED,
            error=None,
        )

    def _reflect_day_edit(self, event: CloudEvent) -> None:
        values = {
            "clock_in": event.clock_in,
            "clock_out": event.clock_out,
            "notice": event.notice,
            "expense_item": event.expense_item,
            "amount": event.amount,
        }
        self.writer.update_day(target_date=event.target_date, **values)
        self.store.record_manual_edit(
            slack_user_id=event.slack_user_id,
            target_date=event.target_date.isoformat(),
            values=values,
            status=ReflectionStatus.REFLECTED,
            error=None,
        )

    def _record_failure(self, event: CloudEvent, error: str) -> None:
        if event.event_type == CloudEventType.PUNCH and event.punch_type and event.tapped_at:
            self.store.upsert_event(
                PunchEvent(
                    slack_event_id=event.event_id,
                    slack_user_id=event.slack_user_id,
                    punch_type=event.punch_type,
                    tapped_at=event.tapped_at,
                    reflected_at=None,
                    note=event.raw_note or "",
                    classification=event.classification,
                    status=ReflectionStatus.FAILED,
                    error=error,
                )
            )
            return
        self.store.record_manual_edit(
            slack_user_id=event.slack_user_id,
            target_date=event.target_date.isoformat(),
            values=_event_values(event),
            status=ReflectionStatus.FAILED,
            error=error,
        )


def _classification_values(classification: Classification | None) -> dict[str, str | int | None]:
    return {
        "clock_in": None,
        "clock_out": None,
        "notice": classification.notice if classification else None,
        "expense_item": classification.expense_item if classification else None,
        "amount": classification.amount if classification else None,
    }


def _event_values(event: CloudEvent) -> dict[str, str | int | None]:
    if event.event_type == CloudEventType.NOTE_REFLECTION:
        return _classification_values(event.classification)
    return {
        "clock_in": event.clock_in,
        "clock_out": event.clock_out,
        "notice": event.notice,
        "expense_item": event.expense_item,
        "amount": event.amount,
    }


def _is_retryable_error(error: str) -> bool:
    lowered = error.lower()
    retryable_markers = ("rpc", "busy", "temporarily", "network", "timeout", "保存", "開けない")
    non_retryable_markers = ("cell already has a value", "target date is outside", "password environment variable")
    if any(marker in lowered for marker in non_retryable_markers):
        return False
    return any(marker in lowered for marker in retryable_markers)
