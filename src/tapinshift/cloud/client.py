from __future__ import annotations

import json
import urllib.request
from datetime import datetime

from .events import CloudEvent, item_to_event


class CloudSyncHttpClient:
    def __init__(self, *, endpoint: str, token: str) -> None:
        self.endpoint = endpoint.rstrip("/")
        self.token = token

    def claim(self, *, claim_token: str, now: datetime, limit: int) -> list[CloudEvent]:
        body = self._post(
            "/sync/claim",
            {
                "claim_token": claim_token,
                "now": now.isoformat(),
                "limit": limit,
            },
        )
        return [item_to_event(item) for item in body.get("events", [])]

    def mark_reflected(self, *, event_id: str, now: datetime) -> None:
        self._post("/sync/reflected", {"event_id": event_id, "now": now.isoformat()})

    def mark_failed(self, *, event_id: str, error: str, retryable: bool, now: datetime) -> None:
        self._post(
            "/sync/failed",
            {
                "event_id": event_id,
                "error": error,
                "retryable": retryable,
                "now": now.isoformat(),
            },
        )

    def _post(self, path: str, payload: dict) -> dict:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(
            f"{self.endpoint}{path}",
            data=data,
            headers={
                "authorization": f"Bearer {self.token}",
                "content-type": "application/json; charset=utf-8",
            },
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=30) as response:  # noqa: S310 - endpoint is user configured.
            return json.loads(response.read().decode("utf-8"))
