from __future__ import annotations

from datetime import date, datetime
from uuid import uuid4

from tapinshift.classifier import RuleBasedClassifier
from tapinshift.config import RoundingConfig
from tapinshift.models import PunchType
from tapinshift.time_rounding import SUPPORTED_ROUNDING_MODES, round_time

from .events import CloudEvent, CloudEventType, SyncStatus, setting_item
from .sync import CloudEventStore


ROUNDING_MODE_SETTING = "time_rounding.mode"


class CloudEventFactory:
    def __init__(self, *, rounding: RoundingConfig, classifier: RuleBasedClassifier) -> None:
        self.rounding = rounding
        self.classifier = classifier

    def punch_event(
        self,
        *,
        slack_user_id: str,
        punch_type: PunchType,
        tapped_at: datetime,
        rounding_mode: str | None = None,
        duplicate_warning: bool = False,
        event_id: str | None = None,
    ) -> CloudEvent:
        mode = rounding_mode or self.rounding.mode
        if mode not in SUPPORTED_ROUNDING_MODES:
            raise ValueError(f"Unsupported rounding mode: {mode}")
        direction = self.rounding.direction_for(punch_type.value)
        reflected_at = round_time(tapped_at, mode=mode, direction=direction)
        return CloudEvent(
            event_id=event_id or _event_id("punch"),
            slack_user_id=slack_user_id,
            event_type=CloudEventType.PUNCH,
            target_date=tapped_at.date(),
            sync_status=SyncStatus.QUEUED,
            created_at=tapped_at,
            updated_at=tapped_at,
            punch_type=punch_type,
            tapped_at=tapped_at,
            reflected_at=reflected_at,
            rounding_mode=mode,
            rounding_direction=direction,
            duplicate_warning=duplicate_warning,
        )

    def note_reflection_event(
        self,
        *,
        slack_user_id: str,
        target_date: date,
        raw_note: str,
        accepted_at: datetime,
        event_id: str | None = None,
    ) -> CloudEvent:
        text = raw_note.strip()
        classification = self.classifier.classify(text)
        return CloudEvent(
            event_id=event_id or _event_id("note"),
            slack_user_id=slack_user_id,
            event_type=CloudEventType.NOTE_REFLECTION,
            target_date=target_date,
            sync_status=SyncStatus.QUEUED,
            created_at=accepted_at,
            updated_at=accepted_at,
            raw_note=text,
            classification=classification,
        )

    def day_edit_event(
        self,
        *,
        slack_user_id: str,
        target_date: date,
        accepted_at: datetime,
        values: dict[str, str | int | None],
        event_id: str | None = None,
    ) -> CloudEvent:
        return CloudEvent(
            event_id=event_id or _event_id("edit"),
            slack_user_id=slack_user_id,
            event_type=CloudEventType.DAY_EDIT,
            target_date=target_date,
            sync_status=SyncStatus.QUEUED,
            created_at=accepted_at,
            updated_at=accepted_at,
            clock_in=_blank_to_none(values.get("clock_in")),
            clock_out=_blank_to_none(values.get("clock_out")),
            notice=_blank_to_none(values.get("notice")),
            expense_item=_blank_to_none(values.get("expense_item")),
            amount=_amount_or_none(values.get("amount")),
        )


class CloudSlackService:
    def __init__(self, *, store: CloudEventStore, factory: CloudEventFactory) -> None:
        self.store = store
        self.factory = factory

    def record_punch(
        self,
        *,
        slack_user_id: str,
        punch_type: PunchType,
        accepted_at: datetime,
        rounding_mode: str | None = None,
    ) -> CloudEvent:
        existing_events = self.store.list_user_events(slack_user_id)
        mode = rounding_mode or self.current_rounding_mode(slack_user_id)
        duplicate_warning = has_same_day_punch(
            existing_events,
            target_date=accepted_at.date(),
            punch_type=punch_type,
        )
        event = self.factory.punch_event(
            slack_user_id=slack_user_id,
            punch_type=punch_type,
            tapped_at=accepted_at,
            rounding_mode=mode,
            duplicate_warning=duplicate_warning,
        )
        self.store.save(event)
        return event

    def update_rounding_mode(self, *, slack_user_id: str, mode: str, updated_at: datetime) -> dict[str, object]:
        item = rounding_setting_item(slack_user_id, mode, updated_at)
        self.store.set_setting(slack_user_id, ROUNDING_MODE_SETTING, mode, updated_at)
        return item

    def current_rounding_mode(self, slack_user_id: str) -> str:
        return self.store.get_setting(slack_user_id, ROUNDING_MODE_SETTING) or self.factory.rounding.mode

    def record_note_reflection(
        self,
        *,
        slack_user_id: str,
        target_date: date,
        raw_note: str,
        accepted_at: datetime,
    ) -> CloudEvent:
        event = self.factory.note_reflection_event(
            slack_user_id=slack_user_id,
            target_date=target_date,
            raw_note=raw_note,
            accepted_at=accepted_at,
        )
        self.store.save(event)
        return event

    def record_day_edit(
        self,
        *,
        slack_user_id: str,
        target_date: date,
        accepted_at: datetime,
        values: dict[str, str | int | None],
    ) -> CloudEvent:
        event = self.factory.day_edit_event(
            slack_user_id=slack_user_id,
            target_date=target_date,
            accepted_at=accepted_at,
            values=values,
        )
        self.store.save(event)
        return event


def rounding_setting_item(slack_user_id: str, mode: str, updated_at: datetime) -> dict[str, object]:
    if mode not in SUPPORTED_ROUNDING_MODES:
        raise ValueError(f"Unsupported rounding mode: {mode}")
    return setting_item(slack_user_id, "time_rounding.mode", mode, updated_at)


def has_same_day_punch(events: list[CloudEvent], *, target_date: date, punch_type: PunchType) -> bool:
    return any(
        event.event_type == CloudEventType.PUNCH
        and event.target_date == target_date
        and event.punch_type == punch_type
        and event.sync_status in {SyncStatus.QUEUED, SyncStatus.CLAIMED, SyncStatus.REFLECTED}
        for event in events
    )


def _blank_to_none(value: str | int | None) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _amount_or_none(value: str | int | None) -> int | None:
    text = _blank_to_none(value)
    if text is None:
        return None
    normalized = text.replace(",", "").replace("，", "").replace("円", "").replace("¥", "").strip()
    return int(normalized) if normalized else None


def _event_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex}"
