from __future__ import annotations

import base64
import json
import os
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any
from urllib.parse import parse_qs
from zoneinfo import ZoneInfo

from tapinshift.models import PunchType
from tapinshift.slack_app import (
    APPLY_NOTE_ACTION,
    CLOCK_IN_ACTION,
    CLOCK_OUT_ACTION,
    DATE_ACTION,
    EDIT_AMOUNT,
    EDIT_CLOCK_IN,
    EDIT_CLOCK_OUT,
    EDIT_EXPENSE,
    EDIT_MODAL_CALLBACK,
    EDIT_NOTICE,
    ROUNDING_MODE_ACTION,
    _edit_modal,
    _home_view,
)
from tapinshift.classifier import RuleBasedClassifier
from tapinshift.config import RoundingConfig

from .events import event_to_item
from .slack_signature import SlackSignatureVerifier
from .business import CloudEventFactory, CloudSlackService
from .dynamodb_store import DynamoDBCloudEventStore
from .slack_client import SlackApiClient, SlackWebClient
from .sync import CloudSyncService

DEFAULT_TIMEZONE = "Asia/Tokyo"


@dataclass(frozen=True)
class CloudConfig:
    slack_signing_secret: str
    sync_token: str | None = None
    slack_bot_token: str | None = None

    @classmethod
    def from_env(cls) -> "CloudConfig":
        return cls(
            slack_signing_secret=os.getenv("SLACK_SIGNING_SECRET", ""),
            sync_token=os.getenv("TAPINSHIFT_SYNC_TOKEN"),
            slack_bot_token=os.getenv("SLACK_BOT_TOKEN"),
        )


@dataclass(frozen=True)
class HttpRequest:
    method: str
    path: str
    headers: dict[str, str]
    body: str

    @classmethod
    def from_lambda_event(cls, event: dict[str, Any]) -> "HttpRequest":
        request_context = event.get("requestContext", {})
        http = request_context.get("http", {})
        raw_body = event.get("body") or ""
        body = base64.b64decode(raw_body).decode("utf-8") if event.get("isBase64Encoded") else raw_body
        return cls(
            method=(http.get("method") or event.get("httpMethod") or "GET").upper(),
            path=event.get("rawPath") or event.get("path") or "/",
            headers=_normalize_headers(event.get("headers") or {}),
            body=body,
        )


def lambda_handler(event: dict[str, Any], context: object) -> dict[str, Any]:  # noqa: ARG001
    config = CloudConfig.from_env()
    sync_service, slack_service = _build_runtime_services()
    return handle_request(
        HttpRequest.from_lambda_event(event),
        config,
        sync_service=sync_service,
        slack_service=slack_service,
    )


def handle_request(
    request: HttpRequest,
    config: CloudConfig,
    sync_service: CloudSyncService | None = None,
    slack_service: CloudSlackService | None = None,
    slack_client: SlackWebClient | None = None,
) -> dict[str, Any]:
    if request.path == "/health":
        return _json_response(200, {"ok": True})

    if request.path.startswith("/slack/"):
        return _handle_slack_request(request, config, slack_service, slack_client)

    if request.path.startswith("/sync/"):
        return _handle_sync_request(request, config, sync_service)

    return _json_response(404, {"error": "not_found"})


def _handle_slack_request(
    request: HttpRequest,
    config: CloudConfig,
    slack_service: CloudSlackService | None,
    slack_client: SlackWebClient | None,
) -> dict[str, Any]:
    if request.method != "POST":
        return _json_response(405, {"error": "method_not_allowed"})
    if not config.slack_signing_secret:
        return _json_response(500, {"error": "slack_signing_secret_not_configured"})

    verifier = SlackSignatureVerifier(config.slack_signing_secret)
    if not verifier.is_valid(headers=request.headers, body=request.body):
        return _json_response(401, {"error": "invalid_slack_signature"})

    payload = _slack_payload(request)
    if payload.get("type") == "url_verification":
        return _json_response(200, {"challenge": payload.get("challenge", "")})

    effective_client = slack_client or (SlackApiClient(config.slack_bot_token) if config.slack_bot_token else None)

    if payload.get("type") == "event_callback" and slack_service is not None and effective_client is not None:
        _handle_event_callback(payload, slack_service, effective_client)
        return _json_response(200, {"ok": True})

    if payload.get("type") == "block_actions" and slack_service is not None:
        event = _record_block_action(payload, slack_service, effective_client)
        if event is not None:
            return _json_response(
                200,
                {
                    "ok": True,
                    "status": "queued",
                    "event": event_to_item(event),
                },
            )

    if payload.get("type") == "view_submission" and slack_service is not None:
        event = _record_view_submission(payload, slack_service, effective_client)
        if event is not None:
            return _json_response(200, {})

    return _json_response(202, {"ok": True, "status": "accepted"})


def _handle_event_callback(payload: dict[str, Any], slack_service: CloudSlackService, slack_client: SlackWebClient) -> None:
    event = payload.get("event", {})
    if event.get("type") == "app_home_opened":
        user_id = event["user"]
        slack_client.views_publish(
            user_id=user_id,
            view=_home_view(rounding_mode=slack_service.current_rounding_mode(user_id)),
        )


def _record_block_action(
    payload: dict[str, Any],
    slack_service: CloudSlackService,
    slack_client: SlackWebClient | None,
) -> Any:
    action = (payload.get("actions") or [{}])[0]
    action_id = action.get("action_id")
    slack_user_id = payload["user"]["id"]
    accepted_at = _action_datetime(action)
    if action_id == CLOCK_IN_ACTION:
        event = slack_service.record_punch(
            slack_user_id=slack_user_id,
            punch_type=PunchType.CLOCK_IN,
            accepted_at=accepted_at,
        )
        _publish_queued_status(slack_client, slack_user_id, event)
        return event
    if action_id == CLOCK_OUT_ACTION:
        event = slack_service.record_punch(
            slack_user_id=slack_user_id,
            punch_type=PunchType.CLOCK_OUT,
            accepted_at=accepted_at,
        )
        _publish_queued_status(slack_client, slack_user_id, event)
        return event
    if action_id == ROUNDING_MODE_ACTION:
        mode = action["selected_option"]["value"]
        slack_service.update_rounding_mode(slack_user_id=slack_user_id, mode=mode, updated_at=accepted_at)
        if slack_client is not None:
            slack_client.views_publish(
                user_id=slack_user_id,
                view=_home_view(status_message=f"丸め単位を変更しました: {mode}", rounding_mode=mode),
            )
        return None
    if action_id == DATE_ACTION:
        selected_date = action["selected_date"]
        if slack_client is not None:
            slack_client.views_open(
                trigger_id=payload["trigger_id"],
                view=_edit_modal(selected_date, []),
            )
        return None
    if action_id == APPLY_NOTE_ACTION:
        event = slack_service.record_note_reflection(
            slack_user_id=slack_user_id,
            target_date=_selected_date(payload, accepted_at),
            raw_note=_note_value(payload),
            accepted_at=accepted_at,
        )
        _publish_queued_status(slack_client, slack_user_id, event)
        return event
    return None


def _publish_queued_status(slack_client: SlackWebClient | None, slack_user_id: str, event: Any) -> None:
    if slack_client is None:
        return
    message = "受け付けました。Windows Agent 起動後に同期します。"
    if getattr(event, "duplicate_warning", False):
        message = "同日の同じ打刻がすでにあります。受け付けましたが、Excel反映時に失敗する可能性があります。"
    slack_client.views_publish(user_id=slack_user_id, view=_home_view(status_message=message))


def _record_view_submission(
    payload: dict[str, Any],
    slack_service: CloudSlackService,
    slack_client: SlackWebClient | None,
) -> Any:
    view = payload.get("view", {})
    if view.get("callback_id") != EDIT_MODAL_CALLBACK:
        return None
    slack_user_id = payload["user"]["id"]
    target_date = datetime.fromisoformat(view["private_metadata"]).date()
    event = slack_service.record_day_edit(
        slack_user_id=slack_user_id,
        target_date=target_date,
        accepted_at=_now(),
        values={
            "clock_in": _view_value(view, EDIT_CLOCK_IN),
            "clock_out": _view_value(view, EDIT_CLOCK_OUT),
            "notice": _view_value(view, EDIT_NOTICE),
            "expense_item": _view_value(view, EDIT_EXPENSE),
            "amount": _view_value(view, EDIT_AMOUNT),
        },
    )
    if slack_client is not None:
        slack_client.views_publish(
            user_id=slack_user_id,
            view=_home_view(status_message="編集内容を受け付けました。Windows Agent 起動後に同期します。"),
        )
    return event


def _handle_sync_request(
    request: HttpRequest,
    config: CloudConfig,
    sync_service: CloudSyncService | None,
) -> dict[str, Any]:
    if not config.sync_token:
        return _json_response(500, {"error": "sync_token_not_configured"})
    expected = f"Bearer {config.sync_token}"
    if request.headers.get("authorization") != expected:
        return _json_response(401, {"error": "unauthorized"})
    if sync_service is None:
        return _json_response(501, {"error": "sync_api_not_implemented"})
    if request.method != "POST":
        return _json_response(405, {"error": "method_not_allowed"})

    payload = json.loads(request.body or "{}")
    try:
        if request.path == "/sync/claim":
            now = _parse_datetime(payload["now"])
            events = sync_service.claim(
                claim_token=str(payload["claim_token"]),
                now=now,
                limit=int(payload.get("limit", 10)),
            )
            return _json_response(200, {"events": [event_to_item(event) for event in events]})
        if request.path == "/sync/reflected":
            event = sync_service.mark_reflected(event_id=str(payload["event_id"]), now=_parse_datetime(payload["now"]))
            return _json_response(200, {"event": event_to_item(event)})
        if request.path == "/sync/failed":
            event = sync_service.mark_failed(
                event_id=str(payload["event_id"]),
                error=str(payload.get("error") or ""),
                retryable=bool(payload.get("retryable", False)),
                now=_parse_datetime(payload["now"]),
            )
            return _json_response(200, {"event": event_to_item(event)})
    except (KeyError, ValueError) as exc:
        return _json_response(400, {"error": str(exc)})

    return _json_response(404, {"error": "not_found"})


def _slack_payload(request: HttpRequest) -> dict[str, Any]:
    content_type = request.headers.get("content-type", "")
    if content_type.startswith("application/json"):
        return json.loads(request.body or "{}")

    form = parse_qs(request.body, keep_blank_values=True)
    if "payload" in form:
        return json.loads(form["payload"][0])
    return {key: values[0] if values else "" for key, values in form.items()}


def _action_datetime(action: dict[str, Any]) -> datetime:
    action_ts = str(action.get("action_ts") or "")
    if action_ts:
        return datetime.fromtimestamp(float(action_ts), tz=_app_timezone())
    return _now()


def _selected_date(payload: dict[str, Any], fallback: datetime) -> Any:
    values = payload.get("view", {}).get("state", {}).get("values", {})
    selected = values.get("tapinshift_date", {}).get(DATE_ACTION, {}).get("selected_date")
    return datetime.fromisoformat(selected).date() if selected else fallback.date()


def _note_value(payload: dict[str, Any]) -> str:
    values = payload.get("view", {}).get("state", {}).get("values", {})
    return (values.get("tapinshift_note", {}).get("tapinshift_note_value", {}).get("value") or "").strip()


def _view_value(view: dict[str, Any], action_id: str) -> str | None:
    values = view.get("state", {}).get("values", {})
    return values.get(action_id, {}).get(action_id, {}).get("value")


def _normalize_headers(headers: dict[str, Any]) -> dict[str, str]:
    return {str(key).lower(): str(value) for key, value in headers.items()}


def _parse_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value)


def _now() -> datetime:
    return datetime.now(_app_timezone())


def _app_timezone() -> ZoneInfo:
    return ZoneInfo(os.getenv("TAPINSHIFT_TIMEZONE", DEFAULT_TIMEZONE))


def _json_response(status_code: int, body: dict[str, Any]) -> dict[str, Any]:
    return {
        "statusCode": status_code,
        "headers": {"content-type": "application/json; charset=utf-8"},
        "body": json.dumps(body, ensure_ascii=False, default=_json_default),
    }


def _json_default(value: object) -> object:
    if isinstance(value, Decimal):
        return int(value) if value == value.to_integral_value() else float(value)
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


def _build_runtime_services() -> tuple[CloudSyncService | None, CloudSlackService | None]:
    table_name = os.getenv("TAPINSHIFT_EVENTS_TABLE")
    if not table_name:
        return None, None
    store = DynamoDBCloudEventStore.from_table_name(table_name)
    factory = CloudEventFactory(
        rounding=RoundingConfig(
            mode=os.getenv("TAPINSHIFT_DEFAULT_ROUNDING_MODE", "none"),
            direction=os.getenv("TAPINSHIFT_DEFAULT_ROUNDING_DIRECTION", "nearest"),
            clock_in_direction=os.getenv("TAPINSHIFT_CLOCK_IN_ROUNDING_DIRECTION", "ceil"),
            clock_out_direction=os.getenv("TAPINSHIFT_CLOCK_OUT_ROUNDING_DIRECTION", "floor"),
        ),
        classifier=RuleBasedClassifier(),
    )
    return CloudSyncService(store), CloudSlackService(store=store, factory=factory)
