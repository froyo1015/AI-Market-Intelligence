"""Free market data adapter backed by Yahoo Finance."""

from __future__ import annotations

from typing import Protocol, Sequence

import pandas as pd
import yfinance as yf

from src.models.schema import AssetType, Instrument


DEFAULT_INSTRUMENTS: Sequence[Instrument] = (
    Instrument("SPY", "SPY", AssetType.EQUITY, stale_after_days=5),
    Instrument("QQQ", "QQQ", AssetType.EQUITY, stale_after_days=5),
    Instrument("NVDA", "NVDA", AssetType.EQUITY, stale_after_days=5),
    Instrument("AAPL", "AAPL", AssetType.EQUITY, stale_after_days=5),
    Instrument("TSLA", "TSLA", AssetType.EQUITY, stale_after_days=5),
    Instrument("BTC-USD", "BTC-USD", AssetType.CRYPTO, stale_after_days=2),
    Instrument("ETH-USD", "ETH-USD", AssetType.CRYPTO, stale_after_days=2),
    Instrument("GOLD", "GC=F", AssetType.COMMODITY, stale_after_days=5),
    Instrument("EURUSD", "EURUSD=X", AssetType.FOREX, stale_after_days=5),
    Instrument("USDJPY", "JPY=X", AssetType.FOREX, stale_after_days=5),
)


class MarketDataError(RuntimeError):
    """Raised when a provider cannot return usable history."""


class MarketDataAdapter(Protocol):
    """Minimal provider boundary used by the snapshot pipeline."""

    source_name: str

    def fetch_history(self, instrument: Instrument, period: str) -> pd.DataFrame:
        """Return daily OHLC history for one instrument."""


class YahooFinanceMarketAdapter:
    """Fetch daily adjusted market history without an API key."""

    source_name = "yahoo_finance"

    def fetch_history(
        self,
        instrument: Instrument,
        period: str = "3mo",
    ) -> pd.DataFrame:
        try:
            history = yf.Ticker(instrument.provider_symbol).history(
                period=period,
                interval="1d",
                auto_adjust=True,
                actions=False,
            )
        except Exception as exc:  # Provider exceptions vary by yfinance version.
            raise MarketDataError(
                f"download failed for {instrument.symbol}: {exc}"
            ) from exc

        if history.empty:
            raise MarketDataError(
                f"provider returned no rows for {instrument.symbol}"
            )

        return history

