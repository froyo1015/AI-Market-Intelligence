from src.brief.generator import generate_brief
from src.brief.templates import movement_label, trend_label


def _record(
    symbol: str,
    daily_change: float = 1.5,
    price: float = 110.0,
    sma20: float = 100.0,
) -> dict:
    return {
        "symbol": symbol,
        "asset_type": "equity",
        "price": price,
        "daily_change": daily_change,
        "weekly_change": 2.5,
        "sma20": sma20,
        "volatility_20d": 18.0,
        "trend": "above_sma20",
        "timestamp": "2026-07-29T00:00:00Z",
        "source": "test_source",
        "status": "success",
    }


def _snapshot() -> dict:
    symbols = (
        "SPY",
        "QQQ",
        "BTC-USD",
        "ETH-USD",
        "GOLD",
        "EURUSD",
        "USDJPY",
    )
    return {
        "generated_at": "2026-07-29T12:00:00Z",
        "source": "test_source",
        "records": [_record(symbol) for symbol in symbols],
    }


def test_rule_thresholds_are_deterministic() -> None:
    assert movement_label(1.01) == "strong positive move"
    assert movement_label(1.0) == "limited daily movement"
    assert movement_label(-1.01) == "negative pressure"
    assert movement_label(-1.0) == "limited daily movement"
    assert trend_label(99.0, 100.0) == "below short-term trend"
    assert trend_label(101.0, 100.0) == "above short-term trend"


def test_generates_required_sections_and_fields() -> None:
    markdown = generate_brief(_snapshot())

    assert markdown.startswith("# AI Market Brief")
    assert "日期: 2026-07-29" in markdown
    for section in (
        "## Market Overview",
        "## Equity Market",
        "## Crypto",
        "## Commodities",
        "## Forex",
    ):
        assert section in markdown
    for symbol in ("SPY", "QQQ", "BTC", "ETH", "Gold", "EURUSD", "USDJPY"):
        assert f"### {symbol}:" in markdown
    for field in (
        "- Price:",
        "- Daily change:",
        "- Weekly change:",
        "- Trend:",
        "- Volatility (20d annualized):",
    ):
        assert field in markdown
    assert "strong positive move" in markdown
    assert "above short-term trend" in markdown


def test_missing_symbol_renders_failed_instead_of_crashing() -> None:
    snapshot = _snapshot()
    snapshot["records"] = [
        record for record in snapshot["records"] if record["symbol"] != "GOLD"
    ]

    markdown = generate_brief(snapshot)
    gold_block = markdown.split("### Gold:", 1)[1].split("## Forex", 1)[0]

    assert "- Price: N/A" in gold_block
    assert "- Status: failed" in gold_block
    assert "daily move unavailable" in gold_block

