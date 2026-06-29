from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum

from tapinshift.models import Classification, PunchType


class CloudEventType(StrEnum):
    PUNCH = "punch"
    NOTE_REFLECTION = "note_reflection"
    DAY_EDIT = "day_edit"


class SyncStatus(StrEnum):
    QUEUED = "queued"
    CLAIMED = "claimed"
    REFLECTED = "reflected"
    FAILED = "failed"


@dataclass(frozen=True)
class CloudEvent:
    event_id: str
    slack_user_id: str
    event_type: CloudEventType
    target_date: date
    sync_status: SyncStatus
    created_at: datetime
    updated_at: datetime
    punch_type: PunchType | None = None
    tapped_at: datetime | None = None
    reflected_at: datetime | None = None
    rounding_mode: str | None = None
    rounding_direction: str | None = None
    duplicate_warning: bool = False
    raw_note: str | None = None
    classification: Classification | None = None
    clock_in: str | None = None
    clock_out: str | None = None
    notice: str | None = None
    expense_item: str | None = None
    amount: int | None = None
    claim_token: str | None = None
    claimed_at: datetime | None = None
    retryable: bool | None = None
    error: str | None = None

    @property
    def pk(self) -> str:
        return f"USER#{self.slack_user_id}"

    @property
    def sk(self) -> str:
        return f"EVENT#{self.target_date.isoformat()}#{self.created_at.isoformat()}#{self.event_id}"

    @property
    def sync_pk(self) -> str:
        return f"SYNC#{self.sync_status.value}"

    @property
    def sync_sk(self) -> str:
        return self.created_at.isoformat()


def event_to_item(event: CloudEvent) -> dict[str, object]:
    item: dict[str, object] = {
        "PK": event.pk,
        "SK": event.sk,
        "GSI1PK": event.sync_pk,
        "GSI1SK": event.sync_sk,
        "event_id": event.event_id,
        "slack_user_id": event.slack_user_id,
        "event_type": event.event_type.value,
        "target_date": event.target_date.isoformat(),
        "sync_status": event.sync_status.value,
        "created_at": event.created_at.isoformat(),
        "updated_at": event.updated_at.isoformat(),
    }
    _put_optional(item, "punch_type", event.punch_type.value if event.punch_type else None)
    _put_optional(item, "tapped_at", _datetime_value(event.tapped_at))
    _put_optional(item, "reflected_at", _datetime_value(event.reflected_at))
    _put_optional(item, "rounding_mode", event.rounding_mode)
    _put_optional(item, "rounding_direction", event.rounding_direction)
    _put_optional(item, "duplicate_warning", event.duplicate_warning if event.duplicate_warning else None)
    _put_optional(item, "raw_note", event.raw_note)
    if event.classification:
        _put_optional(item, "notice", event.classification.notice)
        _put_optional(item, "expense_item", event.classification.expense_item)
        _put_optional(item, "amount", event.classification.amount)
        item["confidence"] = event.classification.confidence
        item["needs_confirmation"] = event.classification.needs_confirmation
    _put_optional(item, "clock_in", event.clock_in)
    _put_optional(item, "clock_out", event.clock_out)
    _put_optional(item, "notice", event.notice)
    _put_optional(item, "expense_item", event.expense_item)
    _put_optional(item, "amount", event.amount)
    _put_optional(item, "claim_token", event.claim_token)
    _put_optional(item, "claimed_at", _datetime_value(event.claimed_at))
    _put_optional(item, "retryable", event.retryable)
    _put_optional(item, "error", event.error)
    return item


def item_to_event(item: dict[str, object]) -> CloudEvent:
    classification = None
    if "confidence" in item:
        classification = Classification(
            notice=_str_or_none(item.get("notice")),
            expense_item=_str_or_none(item.get("expense_item")),
            amount=int(item["amount"]) if item.get("amount") is not None else None,
            confidence=float(item["confidence"]),
            needs_confirmation=bool(item.get("needs_confirmation")),
        )
    return CloudEvent(
        event_id=str(item["event_id"]),
        slack_user_id=str(item["slack_user_id"]),
        event_type=CloudEventType(str(item["event_type"])),
        target_date=date.fromisoformat(str(item["target_date"])),
        sync_status=SyncStatus(str(item["sync_status"])),
        created_at=datetime.fromisoformat(str(item["created_at"])),
        updated_at=datetime.fromisoformat(str(item["updated_at"])),
        punch_type=PunchType(str(item["punch_type"])) if item.get("punch_type") else None,
        tapped_at=_datetime_or_none(item.get("tapped_at")),
        reflected_at=_datetime_or_none(item.get("reflected_at")),
        rounding_mode=_str_or_none(item.get("rounding_mode")),
        rounding_direction=_str_or_none(item.get("rounding_direction")),
        duplicate_warning=bool(item.get("duplicate_warning", False)),
        raw_note=_str_or_none(item.get("raw_note")),
        classification=classification,
        clock_in=_str_or_none(item.get("clock_in")),
        clock_out=_str_or_none(item.get("clock_out")),
        notice=_str_or_none(item.get("notice")) if classification is None else None,
        expense_item=_str_or_none(item.get("expense_item")) if classification is None else None,
        amount=int(item["amount"]) if classification is None and item.get("amount") is not None else None,
        claim_token=_str_or_none(item.get("claim_token")),
        claimed_at=_datetime_or_none(item.get("claimed_at")),
        retryable=bool(item["retryable"]) if item.get("retryable") is not None else None,
        error=_str_or_none(item.get("error")),
    )


def setting_item(slack_user_id: str, key: str, value: str, updated_at: datetime) -> dict[str, object]:
    return {
        "PK": f"USER#{slack_user_id}",
        "SK": f"SETTING#{key}",
        "key": key,
        "value": value,
        "updated_at": updated_at.isoformat(),
    }


def _put_optional(item: dict[str, object], key: str, value: object | None) -> None:
    if value is not None:
        item[key] = value


def _datetime_value(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def _datetime_or_none(value: object | None) -> datetime | None:
    return datetime.fromisoformat(str(value)) if value else None


def _str_or_none(value: object | None) -> str | None:
    return str(value) if value is not None else None
