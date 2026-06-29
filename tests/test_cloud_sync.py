from datetime import date, datetime, timedelta, timezone
import json
import unittest

from tapinshift.cloud.events import CloudEvent, CloudEventType, SyncStatus
from tapinshift.cloud.lambda_app import CloudConfig, HttpRequest, handle_request
from tapinshift.cloud.sync import CloudSyncService, InMemoryCloudEventStore


class CloudSyncServiceTest(unittest.TestCase):
    def test_claim_moves_queued_events_to_claimed(self) -> None:
        now = datetime(2026, 6, 27, 9, 0, tzinfo=timezone.utc)
        store = InMemoryCloudEventStore([_event("evt-1", created_at=now - timedelta(minutes=2))])
        service = CloudSyncService(store)

        claimed = service.claim(claim_token="agent-1", now=now, limit=10)

        self.assertEqual([event.event_id for event in claimed], ["evt-1"])
        self.assertEqual(claimed[0].sync_status, SyncStatus.CLAIMED)
        self.assertEqual(claimed[0].claim_token, "agent-1")
        self.assertEqual(claimed[0].claimed_at, now)

    def test_claim_skips_fresh_claimed_events(self) -> None:
        now = datetime(2026, 6, 27, 9, 0, tzinfo=timezone.utc)
        store = InMemoryCloudEventStore(
            [
                _event(
                    "evt-1",
                    created_at=now - timedelta(minutes=2),
                    sync_status=SyncStatus.CLAIMED,
                    claimed_at=now - timedelta(minutes=3),
                )
            ]
        )
        service = CloudSyncService(store)

        self.assertEqual(service.claim(claim_token="agent-2", now=now), [])

    def test_claim_recovers_stale_claimed_events(self) -> None:
        now = datetime(2026, 6, 27, 9, 0, tzinfo=timezone.utc)
        store = InMemoryCloudEventStore(
            [
                _event(
                    "evt-1",
                    created_at=now - timedelta(minutes=30),
                    sync_status=SyncStatus.CLAIMED,
                    claimed_at=now - timedelta(minutes=11),
                    claim_token="old-agent",
                )
            ]
        )
        service = CloudSyncService(store)

        claimed = service.claim(claim_token="new-agent", now=now)

        self.assertEqual(len(claimed), 1)
        self.assertEqual(claimed[0].claim_token, "new-agent")
        self.assertEqual(claimed[0].claimed_at, now)

    def test_mark_reflected_and_failed_update_status(self) -> None:
        now = datetime(2026, 6, 27, 9, 0, tzinfo=timezone.utc)
        store = InMemoryCloudEventStore([_event("evt-1", created_at=now)])
        service = CloudSyncService(store)

        reflected = service.mark_reflected(event_id="evt-1", now=now + timedelta(minutes=1))
        failed = service.mark_failed(
            event_id="evt-1",
            error="Cell already has a value: F13",
            retryable=False,
            now=now + timedelta(minutes=2),
        )

        self.assertEqual(reflected.sync_status, SyncStatus.REFLECTED)
        self.assertEqual(failed.sync_status, SyncStatus.FAILED)
        self.assertEqual(failed.error, "Cell already has a value: F13")
        self.assertFalse(failed.retryable)


class CloudSyncHttpTest(unittest.TestCase):
    def test_claim_endpoint_returns_claimed_events(self) -> None:
        now = datetime(2026, 6, 27, 9, 0, tzinfo=timezone.utc)
        service = CloudSyncService(InMemoryCloudEventStore([_event("evt-1", created_at=now)]))

        response = handle_request(
            HttpRequest(
                method="POST",
                path="/sync/claim",
                headers={"authorization": "Bearer token"},
                body=json.dumps({"claim_token": "agent-1", "now": now.isoformat()}),
            ),
            CloudConfig(slack_signing_secret="secret", sync_token="token"),
            sync_service=service,
        )

        body = json.loads(response["body"])
        self.assertEqual(response["statusCode"], 200)
        self.assertEqual(body["events"][0]["event_id"], "evt-1")
        self.assertEqual(body["events"][0]["sync_status"], "claimed")
        self.assertEqual(body["events"][0]["claim_token"], "agent-1")

    def test_reflected_endpoint_updates_event_status(self) -> None:
        now = datetime(2026, 6, 27, 9, 0, tzinfo=timezone.utc)
        service = CloudSyncService(InMemoryCloudEventStore([_event("evt-1", created_at=now)]))

        response = handle_request(
            HttpRequest(
                method="POST",
                path="/sync/reflected",
                headers={"authorization": "Bearer token"},
                body=json.dumps({"event_id": "evt-1", "now": now.isoformat()}),
            ),
            CloudConfig(slack_signing_secret="secret", sync_token="token"),
            sync_service=service,
        )

        body = json.loads(response["body"])
        self.assertEqual(response["statusCode"], 200)
        self.assertEqual(body["event"]["sync_status"], "reflected")

    def test_failed_endpoint_updates_event_status(self) -> None:
        now = datetime(2026, 6, 27, 9, 0, tzinfo=timezone.utc)
        service = CloudSyncService(InMemoryCloudEventStore([_event("evt-1", created_at=now)]))

        response = handle_request(
            HttpRequest(
                method="POST",
                path="/sync/failed",
                headers={"authorization": "Bearer token"},
                body=json.dumps(
                    {
                        "event_id": "evt-1",
                        "now": now.isoformat(),
                        "error": "Excel is busy",
                        "retryable": True,
                    }
                ),
            ),
            CloudConfig(slack_signing_secret="secret", sync_token="token"),
            sync_service=service,
        )

        body = json.loads(response["body"])
        self.assertEqual(response["statusCode"], 200)
        self.assertEqual(body["event"]["sync_status"], "failed")
        self.assertTrue(body["event"]["retryable"])
        self.assertEqual(body["event"]["error"], "Excel is busy")


def _event(
    event_id: str,
    *,
    created_at: datetime,
    sync_status: SyncStatus = SyncStatus.QUEUED,
    claimed_at: datetime | None = None,
    claim_token: str | None = None,
) -> CloudEvent:
    return CloudEvent(
        event_id=event_id,
        slack_user_id="U123",
        event_type=CloudEventType.PUNCH,
        target_date=date(2026, 6, 27),
        sync_status=sync_status,
        created_at=created_at,
        updated_at=created_at,
        claimed_at=claimed_at,
        claim_token=claim_token,
    )


if __name__ == "__main__":
    unittest.main()
