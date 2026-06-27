from __future__ import annotations

import argparse
import os
from collections.abc import Callable

from dotenv import load_dotenv

from .classifier import OpenAIClassifier
from .config import load_config
from .excel_writer import ExcelTimesheetWriter
from .service import PunchService
from .slack_app import build_slack_app
from .storage import EventStore


def main() -> None:
    parser = argparse.ArgumentParser(description="Run TapInShift Slack local agent.")
    parser.add_argument("--config", default="config/config.local.json", help="Path to JSON config file.")
    parser.add_argument(
        "--check-config",
        action="store_true",
        help="Validate local configuration and required runtime dependencies without starting Slack.",
    )
    args = parser.parse_args()

    load_dotenv(".env.local")
    config = load_config(args.config)

    if args.check_config:
        raise SystemExit(_check_config(config))

    store = EventStore(config.database_path)
    store.initialize()

    bot_token = config.slack.bot_token
    app_token = config.slack.app_token
    if not bot_token or not app_token:
        raise SystemExit("SLACK_BOT_TOKEN and SLACK_APP_TOKEN must be set.")

    service = PunchService(
        config=config,
        store=store,
        classifier=OpenAIClassifier(config.openai),
        writer=ExcelTimesheetWriter(config.excel),
    )
    app = build_slack_app(service, bot_token=bot_token)

    try:
        from slack_bolt.adapter.socket_mode import SocketModeHandler
    except ImportError as exc:
        raise RuntimeError("slack-bolt socket mode adapter is not installed") from exc

    SocketModeHandler(app, app_token).start()


def _check_config(config) -> int:  # type: ignore[no-untyped-def]
    checks: list[tuple[str, Callable[[], bool], bool]] = [
        ("Slack bot token env", lambda: bool(config.slack.bot_token), True),
        ("Slack app token env", lambda: bool(config.slack.app_token), True),
        ("Excel file exists", lambda: config.excel.path.exists(), True),
        ("Excel password env", lambda: bool(config.excel.password), True),
        ("Database directory writable", lambda: _is_writable_dir(config.database_path.parent), True),
        ("OpenAI API key env", lambda: bool(config.openai.api_key), False),
        ("slack-bolt import", lambda: _can_import("slack_bolt"), True),
        ("xlwings import", lambda: _can_import("xlwings"), True),
        ("openai import", lambda: _can_import("openai"), False),
    ]

    failed_required = False
    for label, check, required in checks:
        ok = check()
        marker = "OK" if ok else ("MISSING" if required else "SKIP")
        print(f"{marker}: {label}")
        failed_required = failed_required or (required and not ok)
    print(f"INFO: Excel path: {config.excel.path}")
    print(f"INFO: Excel sheet: {config.excel.sheet_name}")
    print(f"INFO: Database path: {config.database_path}")
    return 1 if failed_required else 0


def _can_import(module: str) -> bool:
    try:
        __import__(module)
    except ImportError:
        return False
    return True


def _is_writable_dir(path) -> bool:  # type: ignore[no-untyped-def]
    try:
        path.mkdir(parents=True, exist_ok=True)
        probe = path / ".tapinshift-write-test"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
    except OSError:
        return False
    return True


if __name__ == "__main__":
    main()
