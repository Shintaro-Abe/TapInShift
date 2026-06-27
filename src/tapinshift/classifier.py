from __future__ import annotations

import json
import re

from .config import OpenAIConfig
from .models import Classification


AMOUNT_RE = re.compile(r"(?P<amount>\d{2,7})\s*円?")
AMOUNT_TEXT_RE = re.compile(r"[¥￥]?\s*\d[\d,]{1,6}\s*円?")
EXPENSE_KEYWORDS = ("交通費", "電車", "バス", "タクシー", "昼食", "宿泊", "経費", "駐車")
NOTICE_KEYWORDS = ("遅延", "休暇", "早退", "遅刻", "欠勤", "在宅", "直行", "直帰")


def classify_with_rules(note: str) -> Classification:
    text = note.strip()
    if not text:
        return Classification(None, None, None, 1.0, False)

    amount = _extract_amount(text)
    content_text = _strip_amount_text(text)
    has_expense = amount is not None or any(keyword in text for keyword in EXPENSE_KEYWORDS)
    has_notice = any(keyword in text for keyword in NOTICE_KEYWORDS)
    notice, expense_item = _split_notice_and_expense(content_text, has_notice=has_notice, has_expense=has_expense)
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


class OpenAIClassifier:
    def __init__(self, config: OpenAIConfig) -> None:
        self.config = config

    def classify(self, note: str) -> Classification:
        if not note.strip():
            return Classification(None, None, None, 1.0, False)
        if not self.config.api_key:
            return classify_with_rules(note)

        primary = self._classify_with_model(self.config.primary_model, note)
        if primary.confidence >= self.config.confidence_threshold and not primary.needs_confirmation:
            return primary

        fallback = self._classify_with_model(self.config.fallback_model, note)
        if fallback.confidence < self.config.confidence_threshold:
            return _normalize_classification(
                Classification(
                    notice=fallback.notice,
                    expense_item=fallback.expense_item,
                    amount=fallback.amount,
                    confidence=fallback.confidence,
                    needs_confirmation=True,
                )
            )
        return _normalize_classification(fallback)

    def _classify_with_model(self, model: str, note: str) -> Classification:
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RuntimeError("openai package is not installed") from exc

        client = OpenAI(api_key=self.config.api_key)
        response = client.responses.create(
            model=model,
            input=[
                {
                    "role": "system",
                    "content": (
                        "勤務メモをJSONへ分類してください。"
                        "届出内容、経費内容、金額が不明な場合はnullにしてください。"
                        "金額はamountにだけ入れ、noticeやexpense_itemには金額表現を含めないでください。"
                        "届出内容と経費内容が同じメモに含まれる場合は、それぞれ別の項目へ分離してください。"
                        "曖昧な場合はneeds_confirmation=trueにしてください。"
                    ),
                },
                {"role": "user", "content": note},
            ],
            text={
                "format": {
                    "type": "json_schema",
                    "name": "work_note_classification",
                    "schema": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "notice": {"type": ["string", "null"]},
                            "expense_item": {"type": ["string", "null"]},
                            "amount": {"type": ["integer", "null"]},
                            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                            "needs_confirmation": {"type": "boolean"},
                        },
                        "required": [
                            "notice",
                            "expense_item",
                            "amount",
                            "confidence",
                            "needs_confirmation",
                        ],
                    },
                    "strict": True,
                }
            },
        )
        data = json.loads(response.output_text)
        return _normalize_classification(
            Classification(
                notice=data["notice"],
                expense_item=data["expense_item"],
                amount=data["amount"],
                confidence=float(data["confidence"]),
                needs_confirmation=bool(data["needs_confirmation"]),
            )
        )


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


def _split_notice_and_expense(
    text: str | None,
    *,
    has_notice: bool,
    has_expense: bool,
) -> tuple[str | None, str | None]:
    if text is None:
        return None, None
    if has_notice and has_expense:
        expense_span = _expense_span(text)
        if expense_span:
            start, end = expense_span
            expense_item = _cleanup_text(text[start:end])
            notice = _cleanup_text(f"{text[:start]} {text[end:]}")
            return notice or None, expense_item or None
    expense_item = text if has_expense else None
    notice = text if has_notice else None
    return notice, expense_item


def _expense_span(text: str) -> tuple[int, int] | None:
    starts = [index for keyword in EXPENSE_KEYWORDS if (index := text.find(keyword)) >= 0]
    if not starts:
        return None
    start = min(starts)
    notice_starts_after_expense = [
        index for keyword in NOTICE_KEYWORDS if (index := text.find(keyword, start + 1)) >= 0
    ]
    end = min(notice_starts_after_expense) if notice_starts_after_expense else len(text)
    return start, end


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
