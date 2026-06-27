from __future__ import annotations

from datetime import date

from .models import PunchType, ReflectionStatus
from .service import PunchService


CLOCK_IN_ACTION = "tapinshift_clock_in"
CLOCK_OUT_ACTION = "tapinshift_clock_out"
APPLY_NOTE_ACTION = "tapinshift_apply_note"
DATE_ACTION = "tapinshift_select_date"
ROUNDING_MODE_ACTION = "tapinshift_rounding_mode"
EDIT_MODAL_CALLBACK = "tapinshift_edit_day"
NOTE_BLOCK_ID = "tapinshift_note"
NOTE_ACTION_ID = "tapinshift_note_value"
DATE_BLOCK_ID = "tapinshift_date"
ROUNDING_BLOCK_ID = "tapinshift_rounding"
EDIT_CLOCK_IN = "edit_clock_in"
EDIT_CLOCK_OUT = "edit_clock_out"
EDIT_NOTICE = "edit_notice"
EDIT_EXPENSE = "edit_expense"
EDIT_AMOUNT = "edit_amount"
ROUNDING_MODE_LABELS = {
    "none": "丸めなし",
    "5m": "5分",
    "10m": "10分",
    "15m": "15分",
    "20m": "20分",
    "30m": "30分",
}


def build_slack_app(service: PunchService, bot_token: str):
    try:
        from slack_bolt import App
    except ImportError as exc:
        raise RuntimeError("slack-bolt package is not installed") from exc

    app = App(token=bot_token)

    @app.event("app_home_opened")
    def update_home(client, event, logger):  # type: ignore[no-untyped-def]
        client.views_publish(
            user_id=event["user"],
            view=_home_view(initial_date=service.today_iso(), rounding_mode=service.current_rounding_mode()),
        )

    @app.action(CLOCK_IN_ACTION)
    def handle_clock_in(ack, body, client):  # type: ignore[no-untyped-def]
        ack()
        _handle_punch_action(service, body, client, PunchType.CLOCK_IN)

    @app.action(CLOCK_OUT_ACTION)
    def handle_clock_out(ack, body, client):  # type: ignore[no-untyped-def]
        ack()
        _handle_punch_action(service, body, client, PunchType.CLOCK_OUT)

    @app.action(APPLY_NOTE_ACTION)
    def handle_apply_note(ack, body, client):  # type: ignore[no-untyped-def]
        ack()
        user_id = body["user"]["id"]
        note = _extract_note(body)
        target_date = _extract_selected_date(body) or service.today_iso()
        status, error = service.apply_note_to_day(slack_user_id=user_id, target_date=target_date, note=note)
        client.views_publish(
            user_id=user_id,
            view=_home_view(
                status_message=_event_message(status, error),
                initial_date=target_date,
                rounding_mode=service.current_rounding_mode(),
            ),
        )

    @app.action(ROUNDING_MODE_ACTION)
    def handle_rounding_mode(ack, body, client):  # type: ignore[no-untyped-def]
        ack()
        user_id = body["user"]["id"]
        mode = body["actions"][0]["selected_option"]["value"]
        service.update_rounding_mode(mode)
        client.views_publish(
            user_id=user_id,
            view=_home_view(
                status_message=f"丸め単位を{ROUNDING_MODE_LABELS[mode]}に変更しました。",
                initial_date=_extract_selected_date(body) or service.today_iso(),
                rounding_mode=mode,
            ),
        )

    @app.action(DATE_ACTION)
    def handle_date_select(ack, body, client):  # type: ignore[no-untyped-def]
        ack()
        selected_date = body["actions"][0]["selected_date"]
        events = service.get_day_events(selected_date)
        client.views_open(
            trigger_id=body["trigger_id"],
            view=_edit_modal(selected_date, events),
        )

    @app.view(EDIT_MODAL_CALLBACK)
    def handle_edit_submit(ack, body, client):  # type: ignore[no-untyped-def]
        ack()
        user_id = body["user"]["id"]
        target_date = body["view"]["private_metadata"]
        values = _extract_edit_values(body["view"]["state"]["values"])
        status = service.update_day(
            slack_user_id=user_id,
            target_date=target_date,
            values=values,
        )
        client.views_publish(
            user_id=user_id,
            view=_home_view(
                status_message=_event_message(status, None),
                initial_date=service.today_iso(),
                rounding_mode=service.current_rounding_mode(),
            ),
        )

    return app


def _handle_punch_action(service: PunchService, body: dict, client, punch_type: PunchType) -> None:
    user_id = body["user"]["id"]
    event_id = f"{body.get('container', {}).get('view_id', 'home')}:{body['actions'][0]['action_ts']}:{punch_type.value}"
    event = service.handle_punch(
        slack_event_id=event_id,
        slack_user_id=user_id,
        punch_type=punch_type,
    )
    client.views_publish(
        user_id=user_id,
        view=_home_view(
            status_message=_event_message(event.status, event.error),
            initial_date=service.today_iso(),
            rounding_mode=service.current_rounding_mode(),
        ),
    )


def _extract_note(body: dict) -> str:
    values = body.get("view", {}).get("state", {}).get("values", {})
    block = values.get(NOTE_BLOCK_ID, {})
    action = block.get(NOTE_ACTION_ID, {})
    return (action.get("value") or "").strip()


def _event_message(status: ReflectionStatus, error: str | None) -> str:
    if status == ReflectionStatus.REFLECTED:
        return "勤務表へ反映しました。"
    if status == ReflectionStatus.NEEDS_CONFIRMATION:
        return "メモ内容の確認が必要です。SQLiteに確認待ちとして保存しました。"
    if status == ReflectionStatus.FAILED:
        return f"勤務表への反映に失敗しました。SQLiteに未反映として保存しました: {error}"
    return "打刻を保存しました。"


def _home_view(
    status_message: str | None = None,
    initial_date: str | None = None,
    rounding_mode: str = "none",
) -> dict:
    selected_date = initial_date or date.today().isoformat()
    blocks = []
    if status_message:
        blocks.append(
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*状態*: {status_message}"},
            }
        )
    blocks.extend(
        [
            {
                "type": "input",
                "block_id": NOTE_BLOCK_ID,
                "optional": True,
                "element": {
                    "type": "plain_text_input",
                    "action_id": NOTE_ACTION_ID,
                    "placeholder": {"type": "plain_text", "text": "例: 渋谷オフィス 新宿駅-渋谷駅 1200円"},
                },
                "label": {"type": "plain_text", "text": "任意メモ"},
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "出勤"},
                        "style": "primary",
                        "action_id": CLOCK_IN_ACTION,
                    },
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "退勤"},
                        "style": "danger",
                        "action_id": CLOCK_OUT_ACTION,
                    },
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "メモ反映"},
                        "action_id": APPLY_NOTE_ACTION,
                    },
                ],
            },
            {
                "type": "input",
                "block_id": DATE_BLOCK_ID,
                "dispatch_action": True,
                "element": {
                    "type": "datepicker",
                    "initial_date": selected_date,
                    "action_id": DATE_ACTION,
                },
                "label": {"type": "plain_text", "text": "表示・編集する日付"},
            },
            {
                "type": "section",
                "block_id": ROUNDING_BLOCK_ID,
                "text": {"type": "mrkdwn", "text": "*丸め単位*"},
                "accessory": _rounding_mode_select(rounding_mode),
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": "v1はPC起動中のみ反映します。時刻丸めは設定に従って出勤・退勤へ適用されます。",
                    }
                ],
            },
        ]
    )
    return {
        "type": "home",
        "blocks": blocks,
    }


def _rounding_mode_select(rounding_mode: str) -> dict:
    selected_mode = rounding_mode if rounding_mode in ROUNDING_MODE_LABELS else "none"
    options = [
        {
            "text": {"type": "plain_text", "text": label},
            "value": mode,
        }
        for mode, label in ROUNDING_MODE_LABELS.items()
    ]
    initial_option = next(option for option in options if option["value"] == selected_mode)
    return {
        "type": "static_select",
        "action_id": ROUNDING_MODE_ACTION,
        "placeholder": {"type": "plain_text", "text": "丸め単位を選択"},
        "initial_option": initial_option,
        "options": options,
    }


def _edit_modal(selected_date: str, events: list) -> dict:
    initial = _initial_edit_values(events)
    if not events:
        summary = "この日付の入力はまだありません。"
    else:
        lines = []
        for event in events:
            label = "出勤" if event.punch_type == PunchType.CLOCK_IN else "退勤"
            lines.append(f"- {label}: {event.tapped_at.strftime('%H:%M')} / {event.status.value}")
        summary = "\n".join(lines)

    return {
        "type": "modal",
        "callback_id": EDIT_MODAL_CALLBACK,
        "private_metadata": selected_date,
        "title": {"type": "plain_text", "text": "勤務データ"},
        "submit": {"type": "plain_text", "text": "保存"},
        "close": {"type": "plain_text", "text": "閉じる"},
        "blocks": [
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*{selected_date}*\n{summary}"},
            },
            _plain_input("出勤", EDIT_CLOCK_IN, initial["clock_in"], "09:00"),
            _plain_input("退勤", EDIT_CLOCK_OUT, initial["clock_out"], "18:00"),
            _plain_input("届出内容", EDIT_NOTICE, initial["notice"], "渋谷オフィス"),
            _plain_input("経費内容", EDIT_EXPENSE, initial["expense_item"], "新宿駅-渋谷駅"),
            _plain_input("金額", EDIT_AMOUNT, initial["amount"], "320"),
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": "入力した項目だけExcelへ上書きします。空欄の項目は既存の値を保持します（消去はExcelで直接行ってください）。",
                    }
                ],
            },
        ],
    }


def _plain_input(label: str, action_id: str, initial_value: str | None, placeholder: str) -> dict:
    element = {
        "type": "plain_text_input",
        "action_id": action_id,
        "placeholder": {"type": "plain_text", "text": placeholder},
    }
    if initial_value:
        element["initial_value"] = initial_value
    return {
        "type": "input",
        "block_id": action_id,
        "optional": True,
        "element": element,
        "label": {"type": "plain_text", "text": label},
    }


def _initial_edit_values(events: list) -> dict[str, str | None]:
    values: dict[str, str | None] = {
        "clock_in": None,
        "clock_out": None,
        "notice": None,
        "expense_item": None,
        "amount": None,
    }
    for event in events:
        if event.punch_type == PunchType.CLOCK_IN:
            values["clock_in"] = event.tapped_at.strftime("%H:%M")
        elif event.punch_type == PunchType.CLOCK_OUT:
            values["clock_out"] = event.tapped_at.strftime("%H:%M")
        if event.classification:
            values["notice"] = event.classification.notice or values["notice"]
            values["expense_item"] = event.classification.expense_item or values["expense_item"]
            if event.classification.amount is not None:
                values["amount"] = str(event.classification.amount)
    return values


def _extract_edit_values(state_values: dict) -> dict[str, str | int | None]:
    result = {
        "clock_in": _state_value(state_values, EDIT_CLOCK_IN),
        "clock_out": _state_value(state_values, EDIT_CLOCK_OUT),
        "notice": _state_value(state_values, EDIT_NOTICE),
        "expense_item": _state_value(state_values, EDIT_EXPENSE),
        "amount": _state_value(state_values, EDIT_AMOUNT),
    }
    return result


def _state_value(state_values: dict, action_id: str) -> str | None:
    return state_values.get(action_id, {}).get(action_id, {}).get("value")


def _extract_selected_date(body: dict) -> str | None:
    values = body.get("view", {}).get("state", {}).get("values", {})
    return values.get(DATE_BLOCK_ID, {}).get(DATE_ACTION, {}).get("selected_date")
