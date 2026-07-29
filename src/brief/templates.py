"""Markdown layout and deterministic interpretation rules."""

from __future__ import annotations

from typing import Any, Mapping, Optional, Sequence, Tuple

from src.data.asset_metadata import get_asset_metadata
from src.data.data_quality import assess_record_freshness


BRIEF_SECTIONS: Sequence[Tuple[str, Sequence[Tuple[str, str]]]] = (
    (
        "Equity Market",
        (
            ("SPY", "SPY"),
            ("QQQ", "QQQ"),
            ("NVDA", "NVDA"),
            ("AAPL", "AAPL"),
            ("TSLA", "TSLA"),
        ),
    ),
    ("Crypto", (("BTC", "BTC-USD"), ("ETH", "ETH-USD"))),
    ("Commodities", (("Gold", "GOLD"),)),
    ("Forex", (("EURUSD", "EURUSD"), ("USDJPY", "USDJPY"))),
)


def movement_label(daily_change: Optional[float]) -> str:
    """Describe the daily move using the Phase 1.2 thresholds."""
    if daily_change is None:
        return "daily move unavailable"
    if daily_change > 1:
        return "strong positive move"
    if daily_change < -1:
        return "negative pressure"
    return "limited daily movement"


def trend_label(
    price: Optional[float],
    sma20: Optional[float],
    fallback: str = "unavailable",
) -> str:
    """Compare price with SMA20 instead of relying on generated prose."""
    if price is not None and sma20 is not None:
        if price < sma20:
            return "below short-term trend"
        if price > sma20:
            return "above short-term trend"
        return "at short-term trend"

    labels = {
        "below_sma20": "below short-term trend",
        "above_sma20": "above short-term trend",
        "at_sma20": "at short-term trend",
        "insufficient_data": "short-term trend unavailable",
        "unavailable": "short-term trend unavailable",
    }
    return labels.get(fallback, "short-term trend unavailable")


def volatility_label(volatility: Optional[float]) -> str:
    if volatility is None:
        return "volatility unavailable"
    if volatility < 15:
        return "low volatility"
    if volatility < 30:
        return "moderate volatility"
    return "high volatility"


def render_instrument(
    display_symbol: str,
    record: Mapping[str, Any],
    report_generated_at: Any = None,
) -> str:
    """Render one stable Markdown block with all required values."""
    price = _number(record.get("price"))
    daily_change = _number(record.get("daily_change"))
    weekly_change = _number(record.get("weekly_change"))
    sma20 = _number(record.get("sma20"))
    volatility = _number(record.get("volatility_20d"))
    status = str(record.get("status", "failed"))
    symbol = str(record.get("symbol", display_symbol))
    try:
        metadata = get_asset_metadata(symbol)
    except KeyError:
        metadata = None
    freshness = assess_record_freshness(record, report_generated_at)

    return "\n".join(
        (
            (
                f"### {display_symbol}: {metadata.name}"
                if metadata is not None
                else f"### {display_symbol}:"
            ),
            f"- Market: {metadata.market if metadata is not None else 'N/A'}",
            (
                "- Market session: "
                f"{metadata.market_session if metadata is not None else 'N/A'}"
            ),
            (
                "- Price basis: "
                f"{metadata.price_basis if metadata is not None else 'N/A'}"
            ),
            f"- Price: {_format_price(price)}",
            (
                f"- Daily change: {_format_percent(daily_change)}"
                f" — {movement_label(daily_change)}"
            ),
            f"- Weekly change: {_format_percent(weekly_change)}",
            (
                f"- Trend: "
                f"{trend_label(price, sma20, str(record.get('trend', 'unavailable')))}"
                f" (SMA20: {_format_price(sma20)})"
            ),
            (
                f"- Volatility (20d annualized): {_format_unsigned_percent(volatility)}"
                f" — {volatility_label(volatility)}"
            ),
            f"- Status: {status}",
            f"- Data time: {record.get('timestamp', 'N/A')}",
            f"- Freshness: {freshness.display}",
            f"- Source: {record.get('source', 'N/A')}",
        )
    )


def _number(value: Any) -> Optional[float]:
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _format_price(value: Optional[float]) -> str:
    if value is None:
        return "N/A"
    if abs(value) < 10:
        return f"{value:,.6f}"
    return f"{value:,.2f}"


def _format_percent(value: Optional[float]) -> str:
    if value is None:
        return "N/A"
    return f"{value:+.2f}%"


def _format_unsigned_percent(value: Optional[float]) -> str:
    if value is None:
        return "N/A"
    return f"{value:.2f}%"
