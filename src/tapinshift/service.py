from __future__ import annotations

from datetime import date, datetime

from .classifier import OpenAIClassifier
from .config import AppConfig
from .excel_writer import ExcelTimesheetWriter
from .models import PunchEvent, PunchType, ReflectionStatus
from .storage import EventStore
from .time_rounding import SUPPORTED_ROUNDING_MODES, round_time


ROUNDING_MODE_SETTING = "time_rounding.mode"


class PunchService:
    def __init__(
        self,
        config: AppConfig,
        store: EventStore,
        classifier: OpenAIClassifier,
        writer: ExcelTimesheetWriter,
    ) -> None:
        self.config = config
        self.store = store
        self.classifier = classifier
        self.writer = writer

    def handle_punch(
        self,
        slack_event_id: str,
        slack_user_id: str,
        punch_type: PunchType,
        note: str,
        tapped_at: datetime | None = None,
    ) -> PunchEvent:
        tapped = tapped_at or datetime.now(self.config.timezone)
        reflected_time = round_time(
            tapped,
            mode=self.current_rounding_mode(),
            direction=self.config.time_rounding.direction_for(punch_type.value),
        )
        classification = self.classifier.classify(note)
        status = ReflectionStatus.PENDING
        error = None
        reflected_at = None

        if classification.needs_confirmation:
            status = ReflectionStatus.NEEDS_CONFIRMATION
        else:
            try:
                result = self.writer.write_punch(
                    target_date=tapped.date(),
                    punch_type=punch_type,
                    reflected_time=reflected_time,
                    classification=classification,
                )
                status = ReflectionStatus.REFLECTED
                reflected_at = result.reflected_at
            except Exception as exc:  # noqa: BLE001 - persisted for operator review.
                status = ReflectionStatus.FAILED
                error = str(exc)

        event = PunchEvent(
            slack_event_id=slack_event_id,
            slack_user_id=slack_user_id,
            punch_type=punch_type,
            tapped_at=tapped,
            reflected_at=reflected_at,
            note=note,
            classification=classification,
            status=status,
            error=error,
        )
        self.store.upsert_event(event)
        return event

    def get_day_events(self, day: str) -> list[PunchEvent]:
        return self.store.get_day_events(day)

    def today_iso(self) -> str:
        return datetime.now(self.config.timezone).date().isoformat()

    def current_rounding_mode(self) -> str:
        return self.store.get_setting(ROUNDING_MODE_SETTING) or self.config.time_rounding.mode

    def update_rounding_mode(self, mode: str) -> None:
        if mode not in SUPPORTED_ROUNDING_MODES:
            raise ValueError(f"Unsupported rounding mode: {mode}")
        self.store.set_setting(ROUNDING_MODE_SETTING, mode)

    def update_day(
        self,
        *,
        slack_user_id: str,
        target_date: str,
        values: dict[str, str | int | None],
    ) -> ReflectionStatus:
        error = None
        status = ReflectionStatus.REFLECTED
        normalized_values = dict(values)
        try:
            normalized_values = {
                "clock_in": _empty_to_none(values.get("clock_in")),
                "clock_out": _empty_to_none(values.get("clock_out")),
                "notice": _empty_to_none(values.get("notice")),
                "expense_item": _empty_to_none(values.get("expense_item")),
                "amount": _to_int_or_none(values.get("amount")),
            }
            self.writer.update_day(
                target_date=date.fromisoformat(target_date),
                clock_in=normalized_values["clock_in"],
                clock_out=normalized_values["clock_out"],
                notice=normalized_values["notice"],
                expense_item=normalized_values["expense_item"],
                amount=normalized_values["amount"],
            )
        except Exception as exc:  # noqa: BLE001 - persisted for operator review.
            status = ReflectionStatus.FAILED
            error = str(exc)

        self.store.record_manual_edit(
            slack_user_id=slack_user_id,
            target_date=target_date,
            values=normalized_values,
            status=status,
            error=error,
        )
        return status

    def apply_note_to_day(self, *, slack_user_id: str, target_date: str, note: str) -> tuple[ReflectionStatus, str | None]:
        error = None
        values: dict[str, str | int | None] = {
            "clock_in": None,
            "clock_out": None,
            "notice": None,
            "expense_item": None,
            "amount": None,
        }
        text = note.strip()
        if not text:
            error = "No note was provided."
            self.store.record_manual_edit(
                slack_user_id=slack_user_id,
                target_date=target_date,
                values=values,
                status=ReflectionStatus.FAILED,
                error=error,
            )
            return ReflectionStatus.FAILED, error

        status = ReflectionStatus.REFLECTED
        try:
            classification = self.classifier.classify(text)
            values.update(
                {
                    "notice": classification.notice,
                    "expense_item": classification.expense_item,
                    "amount": classification.amount,
                }
            )
            if classification.needs_confirmation:
                status = ReflectionStatus.NEEDS_CONFIRMATION
                error = "Note classification needs confirmation."
            elif not any(values[key] is not None for key in ("notice", "expense_item", "amount")):
                status = ReflectionStatus.FAILED
                error = "No reflected fields were classified from note."
            else:
                self.writer.update_day(
                    target_date=date.fromisoformat(target_date),
                    clock_in=None,
                    clock_out=None,
                    notice=classification.notice,
                    expense_item=classification.expense_item,
                    amount=classification.amount,
                )
        except Exception as exc:  # noqa: BLE001 - persisted for operator review.
            status = ReflectionStatus.FAILED
            error = str(exc)

        self.store.record_manual_edit(
            slack_user_id=slack_user_id,
            target_date=target_date,
            values=values,
            status=status,
            error=error,
        )
        return status, error


def _empty_to_none(value: str | int | None) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _to_int_or_none(value: str | int | None) -> int | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    normalized = text.replace(",", "").replace("，", "").replace("円", "").replace("¥", "").strip()
    if not normalized:
        return None
    return int(normalized)
