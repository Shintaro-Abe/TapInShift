from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class PunchType(StrEnum):
    CLOCK_IN = "clock_in"
    CLOCK_OUT = "clock_out"


class ReflectionStatus(StrEnum):
    PENDING = "pending"
    REFLECTED = "reflected"
    FAILED = "failed"
    NEEDS_CONFIRMATION = "needs_confirmation"


@dataclass(frozen=True)
class Classification:
    notice: str | None
    expense_item: str | None
    amount: int | None
    confidence: float
    needs_confirmation: bool


@dataclass(frozen=True)
class PunchEvent:
    slack_event_id: str
    slack_user_id: str
    punch_type: PunchType
    tapped_at: datetime
    reflected_at: datetime | None
    note: str
    classification: Classification | None
    status: ReflectionStatus
    error: str | None = None

