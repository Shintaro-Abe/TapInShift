from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from zoneinfo import ZoneInfo


@dataclass(frozen=True)
class ExcelColumns:
    table: str | None
    attendance: str | None
    late: str | None
    early: str | None
    date: str
    clock_in: str
    clock_out: str
    notice: str
    expense_item: str
    amount: str


@dataclass(frozen=True)
class ExcelDefaults:
    table: int | None
    attendance: int | None
    late: int | None
    early: int | None


@dataclass(frozen=True)
class ExcelConfig:
    path: Path
    sheet_name: str
    password_env: str
    columns: ExcelColumns
    first_data_row: int
    last_data_row: int | None
    date_format: str
    defaults: ExcelDefaults

    @property
    def password(self) -> str | None:
        return os.getenv(self.password_env)


@dataclass(frozen=True)
class RoundingConfig:
    mode: str
    direction: str
    clock_in_direction: str | None = None
    clock_out_direction: str | None = None

    def direction_for(self, punch_type: str) -> str:
        if punch_type == "clock_in" and self.clock_in_direction:
            return self.clock_in_direction
        if punch_type == "clock_out" and self.clock_out_direction:
            return self.clock_out_direction
        return self.direction


@dataclass(frozen=True)
class SlackConfig:
    bot_token_env: str
    app_token_env: str

    @property
    def bot_token(self) -> str | None:
        return os.getenv(self.bot_token_env)

    @property
    def app_token(self) -> str | None:
        return os.getenv(self.app_token_env)


@dataclass(frozen=True)
class CloudSyncConfig:
    endpoint: str | None
    endpoint_env: str
    token_env: str
    poll_interval_seconds: int
    claim_limit: int

    @property
    def resolved_endpoint(self) -> str | None:
        return self.endpoint or os.getenv(self.endpoint_env)

    @property
    def token(self) -> str | None:
        return os.getenv(self.token_env)


@dataclass(frozen=True)
class AppConfig:
    timezone: ZoneInfo
    database_path: Path
    excel: ExcelConfig
    time_rounding: RoundingConfig
    slack: SlackConfig
    cloud_sync: CloudSyncConfig


def load_config(path: str | Path) -> AppConfig:
    config_path = Path(path)
    raw = json.loads(config_path.read_text(encoding="utf-8"))
    base_dir = config_path.parent

    excel = raw["excel"]
    columns = excel["columns"]
    defaults = excel.get("defaults", {})

    return AppConfig(
        timezone=ZoneInfo(raw.get("timezone", "Asia/Tokyo")),
        database_path=_resolve(base_dir, raw.get("database_path", "data/tapinshift.sqlite3")),
        excel=ExcelConfig(
            path=_resolve(base_dir, excel["path"]),
            sheet_name=excel["sheet_name"],
            password_env=excel.get("password_env", "TAPINSHIFT_EXCEL_PASSWORD"),
            columns=ExcelColumns(
                table=columns.get("table"),
                attendance=columns.get("attendance"),
                late=columns.get("late"),
                early=columns.get("early"),
                date=columns["date"],
                clock_in=columns["clock_in"],
                clock_out=columns["clock_out"],
                notice=columns["notice"],
                expense_item=columns["expense_item"],
                amount=columns["amount"],
            ),
            first_data_row=int(excel.get("first_data_row", 2)),
            last_data_row=int(excel["last_data_row"]) if excel.get("last_data_row") else None,
            date_format=excel.get("date_format", "%Y-%m-%d"),
            defaults=ExcelDefaults(
                table=defaults.get("table"),
                attendance=defaults.get("attendance"),
                late=defaults.get("late"),
                early=defaults.get("early"),
            ),
        ),
        time_rounding=_load_rounding_config(raw.get("time_rounding", {})),
        slack=SlackConfig(
            bot_token_env=raw.get("slack", {}).get("bot_token_env", "SLACK_BOT_TOKEN"),
            app_token_env=raw.get("slack", {}).get("app_token_env", "SLACK_APP_TOKEN"),
        ),
        cloud_sync=_load_cloud_sync_config(raw.get("cloud_sync", {})),
    )


def _resolve(base_dir: Path, value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return (base_dir / path).resolve()


def _load_rounding_config(raw: dict) -> RoundingConfig:
    return RoundingConfig(
        mode=raw.get("mode", "none"),
        direction=raw.get("direction", "nearest"),
        clock_in_direction=raw.get("clock_in_direction"),
        clock_out_direction=raw.get("clock_out_direction"),
    )


def _load_cloud_sync_config(raw: dict) -> CloudSyncConfig:
    return CloudSyncConfig(
        endpoint=raw.get("endpoint"),
        endpoint_env=raw.get("endpoint_env", "TAPINSHIFT_CLOUD_ENDPOINT"),
        token_env=raw.get("token_env", "TAPINSHIFT_SYNC_TOKEN"),
        poll_interval_seconds=int(raw.get("poll_interval_seconds", 300)),
        claim_limit=int(raw.get("claim_limit", 10)),
    )
