from __future__ import annotations

import hashlib
import hmac
import time


class SlackSignatureVerifier:
    def __init__(self, signing_secret: str, *, tolerance_seconds: int = 60 * 5) -> None:
        self.signing_secret = signing_secret.encode("utf-8")
        self.tolerance_seconds = tolerance_seconds

    def is_valid(self, *, headers: dict[str, str], body: str, now: int | None = None) -> bool:
        timestamp = headers.get("x-slack-request-timestamp")
        signature = headers.get("x-slack-signature")
        if not timestamp or not signature:
            return False
        try:
            request_time = int(timestamp)
        except ValueError:
            return False

        current_time = int(time.time()) if now is None else now
        if abs(current_time - request_time) > self.tolerance_seconds:
            return False

        base = f"v0:{timestamp}:{body}".encode("utf-8")
        expected = "v0=" + hmac.new(self.signing_secret, base, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature)
