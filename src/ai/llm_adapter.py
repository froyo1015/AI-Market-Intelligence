"""LLM adapter protocol and deterministic Phase 2.1 mock implementation."""

from __future__ import annotations

import json
from typing import Any, Dict, Mapping, Optional, Protocol, Sequence, Tuple

from src.ai.prompt_builder import INPUT_END_MARKER, INPUT_START_MARKER


class LLMAdapterError(RuntimeError):
    """Raised when an adapter cannot return a usable response."""


class LLMAdapter(Protocol):
    """Minimal interface that a future real provider must implement."""

    provider_name: str

    def generate(self, prompt: str) -> str:
        """Generate Markdown for a fully constructed prompt."""


class MockLLMAdapter:
    """Generate a grounded deterministic response without any API call."""

    provider_name = "mock_llm"

    _SECTIONS: Sequence[Tuple[str, Sequence[str]]] = (
        ("美股", ("SPY", "QQQ", "NVDA", "AAPL", "TSLA")),
        ("Crypto", ("BTC-USD", "ETH-USD")),
        ("黃金", ("GOLD",)),
        ("外匯", ("EURUSD", "USDJPY")),
    )

    def generate(self, prompt: str) -> str:
        payload = _extract_input_payload(prompt)
        snapshot = payload.get("market_snapshot")
        context = payload.get("market_context")
        if not isinstance(snapshot, dict) or not isinstance(context, dict):
            raise LLMAdapterError("prompt input must contain both JSON objects")

        records = _index_records(snapshot.get("records"))
        lines = [
            "# 今日市場焦點",
            "",
            "📌 以下為 Mock Analyst 根據輸入快照整理的測試簡報。",
            *_render_context(context),
            "",
        ]

        for heading, symbols in self._SECTIONS:
            lines.extend((f"## {heading}", ""))
            for symbol in symbols:
                lines.append(_render_record(symbol, records.get(symbol)))
            lines.append("")

        lines.extend(("## 今日風險", ""))
        lines.extend(_render_risks(records, context))
        lines.append("")
        lines.append("本簡報只供研究與流程測試，不構成投資建議。")
        return "\n".join(lines).rstrip() + "\n"


def _extract_input_payload(prompt: str) -> Dict[str, Any]:
    start = prompt.find(INPUT_START_MARKER)
    end = prompt.find(INPUT_END_MARKER)
    if start < 0 or end < 0 or end <= start:
        raise LLMAdapterError("prompt does not contain marked input JSON")

    json_start = start + len(INPUT_START_MARKER)
    raw_payload = prompt[json_start:end].strip()
    try:
        payload = json.loads(raw_payload)
    except json.JSONDecodeError as exc:
        raise LLMAdapterError(f"prompt input JSON is invalid: {exc}") from exc
    if not isinstance(payload, dict):
        raise LLMAdapterError("prompt input JSON root must be an object")
    return payload


def _index_records(value: Any) -> Dict[str, Mapping[str, Any]]:
    if not isinstance(value, list):
        return {}
    records: Dict[str, Mapping[str, Any]] = {}
    for record in value:
        if not isinstance(record, dict):
            continue
        symbol = record.get("symbol")
        if isinstance(symbol, str) and symbol not in records:
            records[symbol] = record
    return records


def _render_record(
    symbol: str,
    record: Optional[Mapping[str, Any]],
) -> str:
    if record is None:
        return f"- {symbol}：資料未知。[來源: 未知; timestamp: 未知]"

    source = _text(record.get("source"))
    timestamp = _text(record.get("timestamp"))
    status = _text(record.get("status"))
    price = record.get("price")
    daily_change = record.get("daily_change")
    trend = _trend_text(record.get("trend"))

    if status == "failed" or price is None:
        return (
            f"- {symbol}：價格未知，資料狀態為 {status or 'failed'}。"
            f"[來源: {source}; timestamp: {timestamp}]"
        )

    stale_note = "；⚠️ 資料已過期" if status == "stale" else ""
    change_text = (
        f"{daily_change}%"
        if isinstance(daily_change, (int, float)) and not isinstance(daily_change, bool)
        else "未知"
    )
    return (
        f"- {symbol}：價格 {price}，日變動 {change_text}，{trend}{stale_note}。"
        f"[來源: {source}; timestamp: {timestamp}]"
    )


def _render_context(context: Mapping[str, Any]) -> Sequence[str]:
    items = context.get("items")
    source = _text(context.get("source"))
    timestamp = _text(context.get("generated_at"))
    if not isinstance(items, list) or not items:
        return (
            (
                "宏觀／新聞背景未知；現階段只可確認市場快照。"
                f"[來源: {source}; timestamp: {timestamp}]"
            ),
        )

    lines = ["", "🗞️ 輸入市場背景："]
    for item in items:
        if not isinstance(item, dict):
            continue
        title = _text(item.get("title"))
        summary = _text(item.get("summary"))
        item_source = _text(item.get("source") or source)
        item_timestamp = _text(item.get("timestamp") or timestamp)
        detail = f" — {summary}" if summary != "未知" else ""
        lines.append(
            f"- {title}{detail}"
            f"[來源: {item_source}; timestamp: {item_timestamp}]"
        )
    return tuple(lines)


def _render_risks(
    records: Mapping[str, Mapping[str, Any]],
    context: Mapping[str, Any],
) -> Sequence[str]:
    lines = []
    stale = sorted(
        symbol
        for symbol, record in records.items()
        if record.get("status") == "stale"
    )
    failed = sorted(
        symbol
        for symbol, record in records.items()
        if record.get("status") == "failed" or record.get("price") is None
    )
    if stale:
        lines.append(f"- 過期資料：{', '.join(stale)}。")
    if failed:
        lines.append(f"- 未知／失敗資料：{', '.join(failed)}。")

    risks = context.get("risks")
    if isinstance(risks, list):
        for risk in risks:
            if isinstance(risk, str):
                lines.append(f"- {risk}")
            elif isinstance(risk, dict):
                lines.append(
                    f"- {_text(risk.get('text'))}"
                    f"[來源: {_text(risk.get('source') or context.get('source'))}; "
                    f"timestamp: {_text(risk.get('timestamp') or context.get('generated_at'))}]"
                )

    if not lines:
        lines.append(
            "- 宏觀／新聞背景未知，無法確認價格變動原因；"
            "免費市場資料亦可能延遲。"
        )
    return tuple(lines)


def _trend_text(value: Any) -> str:
    labels = {
        "above_sma20": "價格高於 SMA20",
        "below_sma20": "價格低於 SMA20",
        "at_sma20": "價格接近 SMA20",
        "insufficient_data": "短期趨勢未知",
        "unavailable": "短期趨勢未知",
    }
    return labels.get(str(value), "短期趨勢未知")


def _text(value: Any) -> str:
    if value is None or value == "":
        return "未知"
    return str(value)

