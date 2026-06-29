import hashlib
import hmac
import json
import time
import unittest
from datetime import datetime
from zoneinfo import ZoneInfo

from tapinshift.cloud.lambda_app import CloudConfig, HttpRequest, handle_request
from tapinshift.cloud.business import CloudEventFactory, CloudSlackService
from tapinshift.cloud.sync import InMemoryCloudEventStore
from tapinshift.cloud.slack_signature import SlackSignatureVerifier
from tapinshift.classifier import RuleBasedClassifier
from tapinshift.config import RoundingConfig
from tapinshift.slack_app import (
    APPLY_NOTE_ACTION,
    CLOCK_IN_ACTION,
    DATE_ACTION,
    EDIT_AMOUNT,
    EDIT_CLOCK_IN,
    EDIT_CLOCK_OUT,
    EDIT_EXPENSE,
    EDIT_MODAL_CALLBACK,
    EDIT_NOTICE,
    NOTE_ACTION_ID,
    NOTE_BLOCK_ID,
    ROUNDING_MODE_ACTION,
)


class SlackSignatureVerifierTest(unittest.TestCase):
    def test_accepts_valid_signature(self) -> None:
        body = '{"type":"url_verification","challenge":"abc"}'
        timestamp = "1800000000"
        signature = _slack_signature("secret", timestamp, body)

        verifier = SlackSignatureVerifier("secret")

        self.assertTrue(
            verifier.is_valid(
                headers={
                    "x-slack-request-timestamp": timestamp,
                    "x-slack-signature": signature,
                },
                body=body,
                now=1800000000,
            )
        )

    def test_rejects_stale_signature(self) -> None:
        body = "{}"
        timestamp = str(int(time.time()) - 600)
        signature = _slack_signature("secret", timestamp, body)

        verifier = SlackSignatureVerifier("secret")

        self.assertFalse(
            verifier.is_valid(
                headers={
                    "x-slack-request-timestamp": timestamp,
                    "x-slack-signature": signature,
                },
                body=body,
            )
        )

    def test_rejects_invalid_signature(self) -> None:
        verifier = SlackSignatureVerifier("secret")

        self.assertFalse(
            verifier.is_valid(
                headers={
                    "x-slack-request-timestamp": "1800000000",
                    "x-slack-signature": "v0=invalid",
                },
                body="{}",
                now=1800000000,
            )
        )


class CloudLambdaAppTest(unittest.TestCase):
    def test_health_check(self) -> None:
        response = handle_request(
            HttpRequest(method="GET", path="/health", headers={}, body=""),
            CloudConfig(slack_signing_secret="secret"),
        )

        self.assertEqual(response["statusCode"], 200)
        self.assertEqual(json.loads(response["body"]), {"ok": True})

    def test_slack_url_verification_returns_challenge(self) -> None:
        body = json.dumps({"type": "url_verification", "challenge": "challenge-value"})
        timestamp = str(int(time.time()))
        response = handle_request(
            HttpRequest(
                method="POST",
                path="/slack/events",
                headers={
                    "content-type": "application/json",
                    "x-slack-request-timestamp": timestamp,
                    "x-slack-signature": _slack_signature("secret", timestamp, body),
                },
                body=body,
            ),
            CloudConfig(slack_signing_secret="secret"),
        )

        self.assertEqual(response["statusCode"], 200)
        self.assertEqual(json.loads(response["body"]), {"challenge": "challenge-value"})

    def test_slack_request_rejects_invalid_signature(self) -> None:
        response = handle_request(
            HttpRequest(
                method="POST",
                path="/slack/events",
                headers={
                    "content-type": "application/json",
                    "x-slack-request-timestamp": "1800000000",
                    "x-slack-signature": "v0=invalid",
                },
                body="{}",
            ),
            CloudConfig(slack_signing_secret="secret"),
        )

        self.assertEqual(response["statusCode"], 401)

    def test_sync_request_requires_bearer_token(self) -> None:
        response = handle_request(
            HttpRequest(method="POST", path="/sync/claim", headers={"authorization": "Bearer wrong"}, body=""),
            CloudConfig(slack_signing_secret="secret", sync_token="expected"),
        )

        self.assertEqual(response["statusCode"], 401)

    def test_sync_request_reaches_not_implemented_after_auth(self) -> None:
        response = handle_request(
            HttpRequest(method="POST", path="/sync/claim", headers={"authorization": "Bearer expected"}, body=""),
            CloudConfig(slack_signing_secret="secret", sync_token="expected"),
        )

        self.assertEqual(response["statusCode"], 501)

    def test_slack_block_action_records_clock_in_event(self) -> None:
        store = InMemoryCloudEventStore()
        slack_service = CloudSlackService(
            store=store,
            factory=CloudEventFactory(
                rounding=RoundingConfig(mode="30m", direction="nearest", clock_in_direction="ceil"),
                classifier=RuleBasedClassifier(),
            ),
        )
        payload = {
            "type": "block_actions",
            "user": {"id": "U123"},
            "actions": [{"action_id": CLOCK_IN_ACTION, "action_ts": "1782533400.000000"}],
        }
        body = "payload=" + json.dumps(payload)
        timestamp = str(int(time.time()))

        response = handle_request(
            HttpRequest(
                method="POST",
                path="/slack/actions",
                headers={
                    "content-type": "application/x-www-form-urlencoded",
                    "x-slack-request-timestamp": timestamp,
                    "x-slack-signature": _slack_signature("secret", timestamp, body),
                },
                body=body,
            ),
            CloudConfig(slack_signing_secret="secret"),
            slack_service=slack_service,
        )

        response_body = json.loads(response["body"])
        saved = store.list_user_events("U123")
        self.assertEqual(response["statusCode"], 200)
        self.assertEqual(response_body["status"], "queued")
        self.assertEqual(len(saved), 1)
        self.assertEqual(saved[0].event_type, "punch")
        self.assertEqual(saved[0].tapped_at, datetime(2026, 6, 27, 13, 10, tzinfo=ZoneInfo("Asia/Tokyo")))
        self.assertEqual(saved[0].reflected_at, datetime(2026, 6, 27, 13, 30, tzinfo=ZoneInfo("Asia/Tokyo")))

    def test_slack_block_action_records_note_reflection_event(self) -> None:
        store = InMemoryCloudEventStore()
        slack_service = CloudSlackService(
            store=store,
            factory=CloudEventFactory(
                rounding=RoundingConfig(mode="none", direction="nearest"),
                classifier=RuleBasedClassifier(),
            ),
        )
        payload = {
            "type": "block_actions",
            "user": {"id": "U123"},
            "actions": [{"action_id": APPLY_NOTE_ACTION, "action_ts": "1782533400.000000"}],
            "view": {
                "state": {
                    "values": {
                        NOTE_BLOCK_ID: {
                            NOTE_ACTION_ID: {
                                "value": "アレア品川、南平⇔市ヶ谷、1134",
                            }
                        }
                    }
                }
            },
        }
        body = "payload=" + json.dumps(payload, ensure_ascii=False)
        timestamp = str(int(time.time()))

        response = handle_request(
            HttpRequest(
                method="POST",
                path="/slack/actions",
                headers={
                    "content-type": "application/x-www-form-urlencoded",
                    "x-slack-request-timestamp": timestamp,
                    "x-slack-signature": _slack_signature("secret", timestamp, body),
                },
                body=body,
            ),
            CloudConfig(slack_signing_secret="secret"),
            slack_service=slack_service,
        )

        saved = store.list_user_events("U123")
        self.assertEqual(response["statusCode"], 200)
        self.assertEqual(saved[0].event_type, "note_reflection")
        self.assertEqual(saved[0].classification.notice, "アレア品川")  # type: ignore[union-attr]

    def test_slack_view_submission_records_day_edit_event(self) -> None:
        store = InMemoryCloudEventStore()
        slack_service = CloudSlackService(
            store=store,
            factory=CloudEventFactory(
                rounding=RoundingConfig(mode="none", direction="nearest"),
                classifier=RuleBasedClassifier(),
            ),
        )
        payload = {
            "type": "view_submission",
            "user": {"id": "U123"},
            "view": {
                "callback_id": EDIT_MODAL_CALLBACK,
                "private_metadata": "2026-06-27",
                "state": {
                    "values": {
                        EDIT_CLOCK_IN: {EDIT_CLOCK_IN: {"value": "09:00"}},
                        EDIT_CLOCK_OUT: {EDIT_CLOCK_OUT: {"value": ""}},
                        EDIT_NOTICE: {EDIT_NOTICE: {"value": "アレア品川"}},
                        EDIT_EXPENSE: {EDIT_EXPENSE: {"value": "南平⇔市ヶ谷"}},
                        EDIT_AMOUNT: {EDIT_AMOUNT: {"value": "1134"}},
                    }
                },
            },
        }
        body = "payload=" + json.dumps(payload, ensure_ascii=False)
        timestamp = str(int(time.time()))

        response = handle_request(
            HttpRequest(
                method="POST",
                path="/slack/actions",
                headers={
                    "content-type": "application/x-www-form-urlencoded",
                    "x-slack-request-timestamp": timestamp,
                    "x-slack-signature": _slack_signature("secret", timestamp, body),
                },
                body=body,
            ),
            CloudConfig(slack_signing_secret="secret"),
            slack_service=slack_service,
        )

        saved = store.list_user_events("U123")
        self.assertEqual(response["statusCode"], 200)
        self.assertEqual(json.loads(response["body"])["response_action"], "clear")
        self.assertEqual(saved[0].event_type, "day_edit")
        self.assertEqual(saved[0].clock_in, "09:00")
        self.assertIsNone(saved[0].clock_out)
        self.assertEqual(saved[0].amount, 1134)

    def test_slack_app_home_opened_publishes_cloud_home(self) -> None:
        store = InMemoryCloudEventStore()
        slack_service = _cloud_slack_service(store)
        client = FakeSlackClient()
        payload = {
            "type": "event_callback",
            "event": {"type": "app_home_opened", "user": "U123"},
        }
        body = json.dumps(payload)
        timestamp = str(int(time.time()))

        response = handle_request(
            HttpRequest(
                method="POST",
                path="/slack/events",
                headers={
                    "content-type": "application/json",
                    "x-slack-request-timestamp": timestamp,
                    "x-slack-signature": _slack_signature("secret", timestamp, body),
                },
                body=body,
            ),
            CloudConfig(slack_signing_secret="secret"),
            slack_service=slack_service,
            slack_client=client,
        )

        self.assertEqual(response["statusCode"], 200)
        self.assertEqual(client.published[0]["user_id"], "U123")

    def test_rounding_mode_action_updates_setting_and_home(self) -> None:
        store = InMemoryCloudEventStore()
        slack_service = _cloud_slack_service(store)
        client = FakeSlackClient()
        payload = {
            "type": "block_actions",
            "user": {"id": "U123"},
            "actions": [
                {
                    "action_id": ROUNDING_MODE_ACTION,
                    "action_ts": "1782533400.000000",
                    "selected_option": {"value": "30m"},
                }
            ],
        }
        body = "payload=" + json.dumps(payload)
        timestamp = str(int(time.time()))

        response = handle_request(
            HttpRequest(
                method="POST",
                path="/slack/actions",
                headers={
                    "content-type": "application/x-www-form-urlencoded",
                    "x-slack-request-timestamp": timestamp,
                    "x-slack-signature": _slack_signature("secret", timestamp, body),
                },
                body=body,
            ),
            CloudConfig(slack_signing_secret="secret"),
            slack_service=slack_service,
            slack_client=client,
        )

        self.assertEqual(response["statusCode"], 202)
        self.assertEqual(store.get_setting("U123", "time_rounding.mode"), "30m")
        self.assertEqual(client.published[0]["user_id"], "U123")

    def test_date_action_opens_edit_modal(self) -> None:
        store = InMemoryCloudEventStore()
        slack_service = _cloud_slack_service(store)
        client = FakeSlackClient()
        payload = {
            "type": "block_actions",
            "user": {"id": "U123"},
            "trigger_id": "trigger-1",
            "actions": [
                {
                    "action_id": DATE_ACTION,
                    "action_ts": "1782533400.000000",
                    "selected_date": "2026-06-27",
                }
            ],
        }
        body = "payload=" + json.dumps(payload)
        timestamp = str(int(time.time()))

        response = handle_request(
            HttpRequest(
                method="POST",
                path="/slack/actions",
                headers={
                    "content-type": "application/x-www-form-urlencoded",
                    "x-slack-request-timestamp": timestamp,
                    "x-slack-signature": _slack_signature("secret", timestamp, body),
                },
                body=body,
            ),
            CloudConfig(slack_signing_secret="secret"),
            slack_service=slack_service,
            slack_client=client,
        )

        self.assertEqual(response["statusCode"], 202)
        self.assertEqual(client.opened[0]["trigger_id"], "trigger-1")
        self.assertEqual(client.opened[0]["view"]["private_metadata"], "2026-06-27")

    def test_duplicate_clock_in_publishes_warning_message(self) -> None:
        store = InMemoryCloudEventStore()
        slack_service = _cloud_slack_service(store)
        client = FakeSlackClient()
        _post_clock_in(slack_service, client)

        response = _post_clock_in(slack_service, client)

        self.assertEqual(response["statusCode"], 200)
        second_message = client.published[1]["view"]["blocks"][0]["text"]["text"]
        self.assertIn("すでにあります", second_message)


def _slack_signature(secret: str, timestamp: str, body: str) -> str:
    base = f"v0:{timestamp}:{body}".encode("utf-8")
    return "v0=" + hmac.new(secret.encode("utf-8"), base, hashlib.sha256).hexdigest()


def _cloud_slack_service(store: InMemoryCloudEventStore) -> CloudSlackService:
    return CloudSlackService(
        store=store,
        factory=CloudEventFactory(
            rounding=RoundingConfig(mode="none", direction="nearest"),
            classifier=RuleBasedClassifier(),
        ),
    )


class FakeSlackClient:
    def __init__(self) -> None:
        self.published = []
        self.opened = []

    def views_publish(self, *, user_id: str, view: dict) -> None:
        self.published.append({"user_id": user_id, "view": view})

    def views_open(self, *, trigger_id: str, view: dict) -> None:
        self.opened.append({"trigger_id": trigger_id, "view": view})


def _post_clock_in(slack_service: CloudSlackService, client: FakeSlackClient):
    payload = {
        "type": "block_actions",
        "user": {"id": "U123"},
        "actions": [{"action_id": CLOCK_IN_ACTION, "action_ts": "1782533400.000000"}],
    }
    body = "payload=" + json.dumps(payload)
    timestamp = str(int(time.time()))
    return handle_request(
        HttpRequest(
            method="POST",
            path="/slack/actions",
            headers={
                "content-type": "application/x-www-form-urlencoded",
                "x-slack-request-timestamp": timestamp,
                "x-slack-signature": _slack_signature("secret", timestamp, body),
            },
            body=body,
        ),
        CloudConfig(slack_signing_secret="secret"),
        slack_service=slack_service,
        slack_client=client,
    )


if __name__ == "__main__":
    unittest.main()
