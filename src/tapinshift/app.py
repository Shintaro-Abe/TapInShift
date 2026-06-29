from __future__ import annotations

import argparse
import os
import socket
import time
from collections.abc import Callable
from datetime import datetime

from dotenv import load_dotenv

from .classifier import RuleBasedClassifier
from .cloud.client import CloudSyncHttpClient
from .cloud.worker import CloudExcelSynchronizer
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
    parser.add_argument("--sync-now", action="store_true", help="Claim cloud events once and reflect them to Excel.")
    parser.add_argument("--poll-cloud", action="store_true", help="Continuously poll cloud events and reflect them to Excel.")
    args = parser.parse_args()

    load_dotenv(".env.local")
    config = load_config(args.config)

    if args.check_config:
        raise SystemExit(_check_config(config))

    store = EventStore(config.database_path)
    store.initialize()

    if args.sync_now or args.poll_cloud:
        synchronizer = _build_cloud_synchronizer(config, store)
        if args.sync_now:
            count = synchronizer.sync_once(now=datetime.now(config.timezone))
            print(f"INFO: Cloud sync reflected attempt count: {count}")
            return
        while True:
            count = synchronizer.sync_once(now=datetime.now(config.timezone))
            print(f"INFO: Cloud sync reflected attempt count: {count}")
            time.sleep(config.cloud_sync.poll_interval_seconds)

    bot_token = config.slack.bot_token
    app_token = config.slack.app_token
    if not bot_token or not app_token:
        raise SystemExit("SLACK_BOT_TOKEN and SLACK_APP_TOKEN must be set.")

    service = PunchService(
        config=config,
        store=store,
        classifier=RuleBasedClassifier(),
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
        ("Cloud sync endpoint", lambda: bool(config.cloud_sync.resolved_endpoint), False),
        ("Cloud sync token env", lambda: bool(config.cloud_sync.token), False),
        ("slack-bolt import", lambda: _can_import("slack_bolt"), True),
        ("xlwings import", lambda: _can_import("xlwings"), True),
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
    print(f"INFO: Cloud sync endpoint: {config.cloud_sync.resolved_endpoint or '(not configured)'}")
    return 1 if failed_required else 0


def _build_cloud_synchronizer(config, store: EventStore) -> CloudExcelSynchronizer:  # type: ignore[no-untyped-def]
    endpoint = config.cloud_sync.resolved_endpoint
    token = config.cloud_sync.token
    if not endpoint:
        raise SystemExit(f"{config.cloud_sync.endpoint_env} or cloud_sync.endpoint must be set for cloud sync.")
    if not token:
        raise SystemExit(f"{config.cloud_sync.token_env} must be set for cloud sync.")
    return CloudExcelSynchronizer(
        client=CloudSyncHttpClient(endpoint=endpoint, token=token),
        writer=ExcelTimesheetWriter(config.excel),
        store=store,
        claim_token=socket.gethostname(),
        claim_limit=config.cloud_sync.claim_limit,
    )


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
