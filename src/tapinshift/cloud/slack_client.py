from __future__ import annotations

import json
import urllib.request
from typing import Protocol


class SlackWebClient(Protocol):
    def views_publish(self, *, user_id: str, view: dict) -> None:
        raise NotImplementedError

    def views_open(self, *, trigger_id: str, view: dict) -> None:
        raise NotImplementedError


class SlackApiClient:
    def __init__(self, bot_token: str, *, base_url: str = "https://slack.com/api") -> None:
        self.bot_token = bot_token
        self.base_url = base_url.rstrip("/")

    def views_publish(self, *, user_id: str, view: dict) -> None:
        self._post("views.publish", {"user_id": user_id, "view": view})

    def views_open(self, *, trigger_id: str, view: dict) -> None:
        self._post("views.open", {"trigger_id": trigger_id, "view": view})

    def _post(self, method: str, payload: dict) -> None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(
            f"{self.base_url}/{method}",
            data=data,
            headers={
                "authorization": f"Bearer {self.bot_token}",
                "content-type": "application/json; charset=utf-8",
            },
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=10) as response:  # noqa: S310 - Slack API endpoint is fixed.
            body = json.loads(response.read().decode("utf-8"))
        if not body.get("ok"):
            raise RuntimeError(f"Slack API {method} failed: {body.get('error')}")
