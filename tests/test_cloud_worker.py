from datetime import date, datetime, timezone
from pathlib import Path
import tempfile
import unittest

from tapinshift.cloud.events import CloudEvent, CloudEventType, SyncStatus
from tapinshift.cloud.worker import CloudExcelSynchronizer
from tapinshift.models import Classification, PunchType, ReflectionStatus
from tapinshift.storage import EventStore


class CloudExcelSynchronizerTest(unittest.TestCase):
    def test_sync_once_reflects_punch_using_cloud_reflected_at(self) -> None:
        reflected_at = datetime(2026, 6, 27, 8, 30, tzinfo=timezone.utc)
        event = _event(
            "evt-1",
            event_type=CloudEventType.PUNCH,
            punch_type=PunchType.CLOCK_IN,
            tapped_at=datetime(2026, 6, 27, 8, 10, tzinfo=timezone.utc),
            reflected_at=reflected_at,
        )
        client = FakeCloudClient([event])
        writer = FakeWriter()
        with tempfile.TemporaryDirectory() as tmp:
            store = EventStore(Path(tmp) / "tapinshift.sqlite3")
            store.initialize()
            sync = CloudExcelSynchronizer(
                client=client,
                writer=writer,
                store=store,
                claim_token="agent-1",
                claim_limit=10,
            )

            count = sync.sync_once(now=datetime(2026, 6, 27, 9, 0, tzinfo=timezone.utc))

            self.assertEqual(count, 1)
            self.assertEqual(writer.write_calls[0]["reflected_time"], reflected_at)
            self.assertEqual(client.reflected, [{"event_id": "evt-1", "claim_token": "agent-1"}])
            self.assertEqual(store.get_day_events("2026-06-27")[0].status, ReflectionStatus.REFLECTED)

    def test_sync_once_reflects_note_event_to_manual_edit_log(self) -> None:
        event = _event(
            "evt-note",
            event_type=CloudEventType.NOTE_REFLECTION,
            classification=Classification("アレア品川", "南平⇔市ヶ谷", 1134, 0.9, False),
        )
        client = FakeCloudClient([event])
        writer = FakeWriter()
        with tempfile.TemporaryDirectory() as tmp:
            store = EventStore(Path(tmp) / "tapinshift.sqlite3")
            store.initialize()
            sync = CloudExcelSynchronizer(
                client=client,
                writer=writer,
                store=store,
                claim_token="agent-1",
                claim_limit=10,
            )

            sync.sync_once(now=datetime(2026, 6, 27, 9, 0, tzinfo=timezone.utc))

            self.assertEqual(writer.update_calls[0]["notice"], "アレア品川")
            self.assertEqual(writer.update_calls[0]["amount"], 1134)
            self.assertEqual(client.reflected, [{"event_id": "evt-note", "claim_token": "agent-1"}])

    def test_sync_once_does_not_reflect_needs_confirmation_note(self) -> None:
        event = _event(
            "evt-note",
            event_type=CloudEventType.NOTE_REFLECTION,
            classification=Classification(None, None, None, 0.2, True),
        )
        client = FakeCloudClient([event])
        writer = FakeWriter()
        with tempfile.TemporaryDirectory() as tmp:
            store = EventStore(Path(tmp) / "tapinshift.sqlite3")
            store.initialize()
            sync = CloudExcelSynchronizer(
                client=client,
                writer=writer,
                store=store,
                claim_token="agent-1",
                claim_limit=10,
            )

            sync.sync_once(now=datetime(2026, 6, 27, 9, 0, tzinfo=timezone.utc))

            self.assertEqual(writer.update_calls, [])
            self.assertEqual(client.reflected, [{"event_id": "evt-note", "claim_token": "agent-1"}])

    def test_sync_once_marks_failed_when_writer_fails(self) -> None:
        event = _event(
            "evt-1",
            event_type=CloudEventType.PUNCH,
            punch_type=PunchType.CLOCK_IN,
            tapped_at=datetime(2026, 6, 27, 8, 10, tzinfo=timezone.utc),
            reflected_at=datetime(2026, 6, 27, 8, 30, tzinfo=timezone.utc),
        )
        client = FakeCloudClient([event])
        writer = FakeWriter(write_error=ValueError("Cell already has a value: F13"))
        with tempfile.TemporaryDirectory() as tmp:
            store = EventStore(Path(tmp) / "tapinshift.sqlite3")
            store.initialize()
            sync = CloudExcelSynchronizer(
                client=client,
                writer=writer,
                store=store,
                claim_token="agent-1",
                claim_limit=10,
            )

            sync.sync_once(now=datetime(2026, 6, 27, 9, 0, tzinfo=timezone.utc))

            self.assertEqual(client.failed[0]["event_id"], "evt-1")
            self.assertFalse(client.failed[0]["retryable"])
            self.assertEqual(store.get_day_events("2026-06-27")[0].status, ReflectionStatus.FAILED)


class FakeCloudClient:
    def __init__(self, events: list[CloudEvent]) -> None:
        self.events = events
        self.reflected = []
        self.failed = []

    def claim(self, *, claim_token: str, now: datetime, limit: int) -> list[CloudEvent]:  # noqa: ARG002
        return self.events[:limit]

    def mark_reflected(self, *, event_id: str, claim_token: str, now: datetime) -> None:  # noqa: ARG002
        self.reflected.append({"event_id": event_id, "claim_token": claim_token})

    def mark_failed(self, *, event_id: str, claim_token: str, error: str, retryable: bool, now: datetime) -> None:  # noqa: ARG002
        self.failed.append({"event_id": event_id, "claim_token": claim_token, "error": error, "retryable": retryable})


class FakeWriter:
    def __init__(self, write_error: Exception | None = None) -> None:
        self.write_error = write_error
        self.write_calls = []
        self.update_calls = []

    def write_punch(self, **kwargs):
        self.write_calls.append(kwargs)
        if self.write_error:
            raise self.write_error
        return type("Result", (), {"reflected_at": kwargs["reflected_time"], "row": 7})()

    def update_day(self, **kwargs):
        self.update_calls.append(kwargs)
        return type("Result", (), {"reflected_at": datetime(2026, 6, 27, 9, 0), "row": 7})()


def _event(
    event_id: str,
    *,
    event_type: CloudEventType,
    punch_type: PunchType | None = None,
    tapped_at: datetime | None = None,
    reflected_at: datetime | None = None,
    classification: Classification | None = None,
) -> CloudEvent:
    created_at = datetime(2026, 6, 27, 8, 10, tzinfo=timezone.utc)
    return CloudEvent(
        event_id=event_id,
        slack_user_id="U123",
        event_type=event_type,
        target_date=date(2026, 6, 27),
        sync_status=SyncStatus.CLAIMED,
        created_at=created_at,
        updated_at=created_at,
        punch_type=punch_type,
        tapped_at=tapped_at,
        reflected_at=reflected_at,
        classification=classification,
    )


if __name__ == "__main__":
    unittest.main()
