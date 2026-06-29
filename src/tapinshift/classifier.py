from __future__ import annotations

import re

from .models import Classification


AMOUNT_RE = re.compile(r"(?P<amount>\d{2,7})\s*円?")
AMOUNT_TEXT_RE = re.compile(r"[¥￥]?\s*\d[\d,]{1,6}\s*円?")
EXPENSE_LABELS = ("交通費", "経費", "電車", "バス", "タクシー", "昼食", "宿泊", "駐車")
LOCATION_KEYWORDS = ("拠点", "本社", "支社", "営業所", "オフィス", "ビル", "タワー", "センター", "駅")
ROUTE_SEPARATORS = ("-", "ー", "〜", "~", "→", "->", "⇔", "↔", "<->", "から")


def classify_with_rules(note: str) -> Classification:
    text = note.strip()
    if not text:
        return Classification(None, None, None, 1.0, False)

    amount = _extract_amount(text)
    content_text = _strip_amount_text(text)
    notice, expense_item = _classify_content(content_text, has_amount=amount is not None)
    confidence = 0.75 if expense_item or notice else 0.35

    return _normalize_classification(
        Classification(
            notice=notice,
            expense_item=expense_item,
            amount=amount,
            confidence=confidence,
            needs_confirmation=confidence < 0.75,
        )
    )


class RuleBasedClassifier:
    def classify(self, note: str) -> Classification:
        return classify_with_rules(note)


def _extract_amount(text: str) -> int | None:
    match = AMOUNT_RE.search(text.replace(",", ""))
    if not match:
        return None
    return int(match.group("amount"))


def _strip_amount_text(text: str | None) -> str | None:
    if text is None:
        return None
    stripped = AMOUNT_TEXT_RE.sub("", text)
    stripped = _cleanup_text(stripped)
    return stripped or None


def _classify_content(text: str | None, *, has_amount: bool) -> tuple[str | None, str | None]:
    if text is None:
        return None, None
    if not has_amount:
        return (text, None) if _looks_like_location(text) else (None, None)

    expense_text = _strip_expense_labels(text)
    if expense_text is None:
        return None, None

    parts = expense_text.split()
    if len(parts) <= 1:
        return None, expense_text

    route_parts = [part for part in parts if _looks_like_route(part)]
    if route_parts:
        notice = _cleanup_text(" ".join(part for part in parts if part not in route_parts))
        expense_item = _cleanup_text(" ".join(route_parts))
        return notice or None, expense_item or None

    return None, expense_text


def _looks_like_location(text: str) -> bool:
    return any(keyword in text for keyword in LOCATION_KEYWORDS)


def _looks_like_route(text: str) -> bool:
    return any(separator in text for separator in ROUTE_SEPARATORS)


def _strip_expense_labels(text: str | None) -> str | None:
    if text is None:
        return None
    result = text
    for label in EXPENSE_LABELS:
        result = result.replace(label, " ")
    cleaned = _cleanup_text(result)
    return cleaned or None


def _cleanup_text(text: str) -> str:
    cleaned = re.sub(r"\s+", " ", text)
    cleaned = re.sub(r"\s*[、,，]\s*", " ", cleaned)
    return cleaned.strip(" 　、,，")


def _normalize_classification(classification: Classification) -> Classification:
    return Classification(
        notice=_strip_amount_text(classification.notice),
        expense_item=_strip_amount_text(classification.expense_item),
        amount=classification.amount,
        confidence=classification.confidence,
        needs_confirmation=classification.needs_confirmation,
    )
