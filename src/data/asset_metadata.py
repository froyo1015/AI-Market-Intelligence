"""Static asset metadata used by reports without changing the core pipeline."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, Mapping


@dataclass(frozen=True)
class AssetMetadata:
    """Human-readable market and timestamp semantics for one instrument."""

    symbol: str
    display_symbol: str
    name: str
    asset_type: str
    provider_symbol: str
    market: str
    market_session: str
    market_timezone: str
    price_basis: str
    timestamp_semantics: str
    current_after_hours: float
    stale_after_hours: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


_US_EQUITY_SESSION = "美股核心交易時段 09:30–16:00 ET（交易日）"
_US_EQUITY_BASIS = "Yahoo Finance 調整後日線價格（非即時報價）"
_DAILY_BAR_TIMESTAMP = "provider daily bar timestamp；不代表即時成交時間"


ASSET_METADATA: Mapping[str, AssetMetadata] = {
    "SPY": AssetMetadata(
        symbol="SPY",
        display_symbol="SPY",
        name="SPDR S&P 500 ETF Trust",
        asset_type="equity",
        provider_symbol="SPY",
        market="NYSE Arca",
        market_session=_US_EQUITY_SESSION,
        market_timezone="America/New_York",
        price_basis=_US_EQUITY_BASIS,
        timestamp_semantics=_DAILY_BAR_TIMESTAMP,
        current_after_hours=36,
        stale_after_hours=120,
    ),
    "QQQ": AssetMetadata(
        symbol="QQQ",
        display_symbol="QQQ",
        name="Invesco QQQ Trust",
        asset_type="equity",
        provider_symbol="QQQ",
        market="NASDAQ",
        market_session=_US_EQUITY_SESSION,
        market_timezone="America/New_York",
        price_basis=_US_EQUITY_BASIS,
        timestamp_semantics=_DAILY_BAR_TIMESTAMP,
        current_after_hours=36,
        stale_after_hours=120,
    ),
    "NVDA": AssetMetadata(
        symbol="NVDA",
        display_symbol="NVDA",
        name="NVIDIA",
        asset_type="equity",
        provider_symbol="NVDA",
        market="NASDAQ",
        market_session=_US_EQUITY_SESSION,
        market_timezone="America/New_York",
        price_basis=_US_EQUITY_BASIS,
        timestamp_semantics=_DAILY_BAR_TIMESTAMP,
        current_after_hours=36,
        stale_after_hours=120,
    ),
    "AAPL": AssetMetadata(
        symbol="AAPL",
        display_symbol="AAPL",
        name="Apple",
        asset_type="equity",
        provider_symbol="AAPL",
        market="NASDAQ",
        market_session=_US_EQUITY_SESSION,
        market_timezone="America/New_York",
        price_basis=_US_EQUITY_BASIS,
        timestamp_semantics=_DAILY_BAR_TIMESTAMP,
        current_after_hours=36,
        stale_after_hours=120,
    ),
    "TSLA": AssetMetadata(
        symbol="TSLA",
        display_symbol="TSLA",
        name="Tesla",
        asset_type="equity",
        provider_symbol="TSLA",
        market="NASDAQ",
        market_session=_US_EQUITY_SESSION,
        market_timezone="America/New_York",
        price_basis=_US_EQUITY_BASIS,
        timestamp_semantics=_DAILY_BAR_TIMESTAMP,
        current_after_hours=36,
        stale_after_hours=120,
    ),
    "BTC-USD": AssetMetadata(
        symbol="BTC-USD",
        display_symbol="BTC",
        name="Bitcoin / U.S. Dollar",
        asset_type="crypto",
        provider_symbol="BTC-USD",
        market="Global crypto market",
        market_session="24/7",
        market_timezone="UTC",
        price_basis="Yahoo Finance crypto 日線價格（USD；非即時報價）",
        timestamp_semantics=_DAILY_BAR_TIMESTAMP,
        current_after_hours=30,
        stale_after_hours=48,
    ),
    "ETH-USD": AssetMetadata(
        symbol="ETH-USD",
        display_symbol="ETH",
        name="Ether / U.S. Dollar",
        asset_type="crypto",
        provider_symbol="ETH-USD",
        market="Global crypto market",
        market_session="24/7",
        market_timezone="UTC",
        price_basis="Yahoo Finance crypto 日線價格（USD；非即時報價）",
        timestamp_semantics=_DAILY_BAR_TIMESTAMP,
        current_after_hours=30,
        stale_after_hours=48,
    ),
    "GOLD": AssetMetadata(
        symbol="GOLD",
        display_symbol="Gold",
        name="COMEX Gold Futures",
        asset_type="commodity",
        provider_symbol="GC=F",
        market="COMEX / CME Globex",
        market_session="星期日至星期五接近 24 小時；每日維護休市（CT）",
        market_timezone="America/Chicago",
        price_basis="近月黃金期貨日線（USD/oz；不是現貨金）",
        timestamp_semantics=_DAILY_BAR_TIMESTAMP,
        current_after_hours=36,
        stale_after_hours=120,
    ),
    "EURUSD": AssetMetadata(
        symbol="EURUSD",
        display_symbol="EURUSD",
        name="Euro / U.S. Dollar",
        asset_type="forex",
        provider_symbol="EURUSD=X",
        market="Global OTC FX",
        market_session="24/5（星期日至星期五；indicative）",
        market_timezone="UTC",
        price_basis="Yahoo Finance FX 日線；每 1 EUR 的 USD 報價",
        timestamp_semantics=_DAILY_BAR_TIMESTAMP,
        current_after_hours=36,
        stale_after_hours=120,
    ),
    "USDJPY": AssetMetadata(
        symbol="USDJPY",
        display_symbol="USDJPY",
        name="U.S. Dollar / Japanese Yen",
        asset_type="forex",
        provider_symbol="JPY=X",
        market="Global OTC FX",
        market_session="24/5（星期日至星期五；indicative）",
        market_timezone="UTC",
        price_basis="Yahoo Finance FX 日線；每 1 USD 的 JPY 報價",
        timestamp_semantics=_DAILY_BAR_TIMESTAMP,
        current_after_hours=36,
        stale_after_hours=120,
    ),
}

SYMBOL_ALIASES: Mapping[str, str] = {
    "BTC": "BTC-USD",
    "ETH": "ETH-USD",
    "Gold": "GOLD",
}


def canonical_symbol(symbol: str) -> str:
    return SYMBOL_ALIASES.get(symbol, symbol)


def get_asset_metadata(symbol: str) -> AssetMetadata:
    """Return metadata for a supported canonical or display symbol."""
    canonical = canonical_symbol(symbol)
    try:
        return ASSET_METADATA[canonical]
    except KeyError as exc:
        raise KeyError(f"unsupported asset metadata symbol: {symbol}") from exc
