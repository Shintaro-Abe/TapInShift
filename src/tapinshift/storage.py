from __future__ import annotations

import sqlite3
from contextlib import closing
from datetime import datetime
from pathlib import Path

from .models import Classification, PunchEvent, PunchType, ReflectionStatus


class EventStore:
    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path
        self.database_path.parent.mkdir(parents=True, exist_ok=True)

    def initialize(self) -> None:
        with closing(self._connect()) as conn:
            with conn:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS punch_events (
                        slack_event_id TEXT PRIMARY KEY,
                        slack_user_id TEXT NOT NULL,
                        punch_type TEXT NOT NULL,
                        tapped_at TEXT NOT NULL,
                        reflected_at TEXT,
                        note TEXT NOT NULL,
                        notice TEXT,
                        expense_item TEXT,
                        amount INTEGER,
                        confidence REAL,
                        needs_confirmation INTEGER,
                        status TEXT NOT NULL,
                        error TEXT,
                        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                    )
                    """
                )
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS manual_edits (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        slack_user_id TEXT NOT NULL,
                        target_date TEXT NOT NULL,
                        clock_in TEXT,
                        clock_out TEXT,
                        notice TEXT,
                        expense_item TEXT,
                        amount INTEGER,
                        status TEXT NOT NULL,
                        error TEXT,
                        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                    )
                    """
                )
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS app_settings (
                        key TEXT PRIMARY KEY,
                        value TEXT NOT NULL,
                        updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                    )
                    """
                )

    def upsert_event(self, event: PunchEvent) -> None:
        classification = event.classification
        with closing(self._connect()) as conn:
            with conn:
                conn.execute(
                    """
                    INSERT INTO punch_events (
                        slack_event_id, slack_user_id, punch_type, tapped_at, reflected_at,
                        note, notice, expense_item, amount, confidence, needs_confirmation,
                        status, error
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(slack_event_id) DO UPDATE SET
                        reflected_at = excluded.reflected_at,
                        notice = excluded.notice,
                        expense_item = excluded.expense_item,
                        amount = excluded.amount,
                        confidence = excluded.confidence,
                        needs_confirmation = excluded.needs_confirmation,
                        status = excluded.status,
                        error = excluded.error,
                        updated_at = CURRENT_TIMESTAMP
                    """,
                    (
                        event.slack_event_id,
                        event.slack_user_id,
                        event.punch_type.value,
                        event.tapped_at.isoformat(),
                        event.reflected_at.isoformat() if event.reflected_at else None,
                        event.note,
                        classification.notice if classification else None,
                        classification.expense_item if classification else None,
                        classification.amount if classification else None,
                        classification.confidence if classification else None,
                        int(classification.needs_confirmation) if classification else None,
                        event.status.value,
                        event.error,
                    ),
                )

    def get_day_events(self, day: str) -> list[PunchEvent]:
        with closing(self._connect()) as conn:
            rows = conn.execute(
                """
                SELECT slack_event_id, slack_user_id, punch_type, tapped_at, reflected_at,
                       note, notice, expense_item, amount, confidence, needs_confirmation,
                       status, error
                FROM punch_events
                WHERE substr(tapped_at, 1, 10) = ?
                ORDER BY tapped_at ASC
                """,
                (day,),
            ).fetchall()
        return [_row_to_event(row) for row in rows]

    def record_manual_edit(
        self,
        *,
        slack_user_id: str,
        target_date: str,
        values: dict[str, str | int | None],
        status: ReflectionStatus,
        error: str | None,
    ) -> None:
        with closing(self._connect()) as conn:
            with conn:
                conn.execute(
                    """
                    INSERT INTO manual_edits (
                        slack_user_id, target_date, clock_in, clock_out, notice,
                        expense_item, amount, status, error
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        slack_user_id,
                        target_date,
                        values.get("clock_in"),
                        values.get("clock_out"),
                        values.get("notice"),
                        values.get("expense_item"),
                        values.get("amount"),
                        status.value,
                        error,
                    ),
                )

    def get_setting(self, key: str) -> str | None:
        with closing(self._connect()) as conn:
            row = conn.execute("SELECT value FROM app_settings WHERE key = ?", (key,)).fetchone()
        return row[0] if row else None

    def set_setting(self, key: str, value: str) -> None:
        with closing(self._connect()) as conn:
            with conn:
                conn.execute(
                    """
                    INSERT INTO app_settings (key, value)
                    VALUES (?, ?)
                    ON CONFLICT(key) DO UPDATE SET
                        value = excluded.value,
                        updated_at = CURRENT_TIMESTAMP
                    """,
                    (key, value),
                )

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.database_path)


def _row_to_event(row: tuple) -> PunchEvent:
    classification = None
    if row[9] is not None:
        classification = Classification(
            notice=row[6],
            expense_item=row[7],
            amount=row[8],
            confidence=float(row[9]),
            needs_confirmation=bool(row[10]),
        )
    return PunchEvent(
        slack_event_id=row[0],
        slack_user_id=row[1],
        punch_type=PunchType(row[2]),
        tapped_at=datetime.fromisoformat(row[3]),
        reflected_at=datetime.fromisoformat(row[4]) if row[4] else None,
        note=row[5],
        classification=classification,
        status=ReflectionStatus(row[11]),
        error=row[12],
    )
