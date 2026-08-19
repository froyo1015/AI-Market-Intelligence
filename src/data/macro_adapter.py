"""Free, bounded adapter for the Phase 6.2-A macro market proxies."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, Sequence

import pandas as pd
import yfinance as yf


@dataclass(frozen=True)
class MacroInstrument:
    """Provider mapping and evidence semantics for one macro market proxy."""

    symbol: str
    provider_symbol: str
    name: str
    metric: str
    value_unit: str
    change_metric: str
    change_unit: str
    stale_after_days: int
    price_basis: str
    provider_url: str
    semantic_reference_url: str
    asset_mapping: tuple[str, ...]
    source_confidence: float = 0.75


DEFAULT_MACRO_INSTRUMENTS: Sequence[MacroInstrument] = (
    MacroInstrument(
        symbol="DXY",
        provider_symbol="DX-Y.NYB",
        name="U.S. Dollar Index",
        metric="index_level",
        value_unit="index_points",
        change_metric="daily_change_pct",
        change_unit="percent",
        stale_after_days=5,
        price_basis="Yahoo Finance delayed daily U.S. Dollar Index level",
        provider_url="https://finance.yahoo.com/quote/DX-Y.NYB/",
        semantic_reference_url=(
            "https://www.ice.com/products/194/US-Dollar-Index-USDX-Futures"
        ),
        asset_mapping=(
            "EURUSD",
            "USDJPY",
            "GOLD",
            "SPY",
            "QQQ",
            "BTC-USD",
        ),
    ),
    MacroInstrument(
        symbol="US10Y",
        provider_symbol="^TNX",
        name="U.S. 10-Year Treasury Yield",
        metric="yield",
        value_unit="percent",
        change_metric="daily_change_bps",
        change_unit="basis_points",
        stale_after_days=5,
        price_basis="Yahoo Finance delayed daily ^TNX yield level",
        provider_url="https://finance.yahoo.com/quote/%5ETNX/",
        semantic_reference_url=(
            "https://home.treasury.gov/resource-center/data-chart-center/"
            "interest-rates/TextView?type=daily_treasury_yield_curve"
        ),
        asset_mapping=("SPY", "QQQ", "GOLD", "DXY", "USDJPY"),
    ),
    MacroInstrument(
        symbol="VIX",
        provider_symbol="^VIX",
        name="Cboe Volatility Index",
        metric="index_level",
        value_unit="index_points",
        change_metric="daily_change_pct",
        change_unit="percent",
        stale_after_days=5,
        price_basis="Yahoo Finance delayed daily Cboe VIX Index level",
        provider_url="https://finance.yahoo.com/quote/%5EVIX/",
        semantic_reference_url="https://www.cboe.com/tradable-products/vix",
        asset_mapping=("SPY", "QQQ", "BTC-USD"),
    ),
    MacroInstrument(
        symbol="OIL",
        provider_symbol="CL=F",
        name="WTI Crude Oil Front-Month Futures",
        metric="futures_price",
        value_unit="USD_per_barrel",
        change_metric="daily_change_pct",
        change_unit="percent",
        stale_after_days=5,
        price_basis=(
            "Yahoo Finance delayed front-month WTI futures daily price; "
            "not a physical spot price"
        ),
        provider_url="https://finance.yahoo.com/quote/CL%3DF/",
        semantic_reference_url=(
            "https://www.cmegroup.com/markets/energy/wti-crude-oil-futures.html"
        ),
        asset_mapping=("SPY", "QQQ", "GOLD", "DXY"),
    ),
)


class MacroDataError(RuntimeError):
    """Raised when a macro provider returns no usable history."""


class MacroDataAdapter(Protocol):
    source_name: str

    def fetch_history(
        self, instrument: MacroInstrument, period: str
    ) -> pd.DataFrame:
        """Return daily price or index history for one macro proxy."""


class YahooFinanceMacroAdapter:
    """Fetch the four approved macro proxies without an API key."""

    source_name = "yahoo_finance"

    def fetch_history(
        self,
        instrument: MacroInstrument,
        period: str = "3mo",
    ) -> pd.DataFrame:
        try:
            history = yf.Ticker(instrument.provider_symbol).history(
                period=period,
                interval="1d",
                auto_adjust=True,
                actions=False,
            )
        except Exception as exc:
            raise MacroDataError(
                f"download failed for {instrument.symbol}: {exc}"
            ) from exc
        if history.empty:
            raise MacroDataError(
                f"provider returned no rows for {instrument.symbol}"
            )
        return history
