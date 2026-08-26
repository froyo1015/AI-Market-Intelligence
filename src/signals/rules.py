"""Frozen Phase 6.3-A cross-asset relationship rule registry."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional, Tuple


RULE_SET_VERSION = "cross_asset_rules_v1"
MAXIMUM_TIME_GAP_HOURS = 36.0


@dataclass(frozen=True)
class RequiredObservation:
    asset: str
    metric: str
    unit: str
    minimum_absolute_move: float


@dataclass(frozen=True)
class CrossAssetRule:
    rule_id: str
    relationship_kind: str
    label: str
    operator: str
    required_inputs: Tuple[RequiredObservation, ...]
    maximum_time_gap_hours: float = MAXIMUM_TIME_GAP_HOURS
    spread_threshold: Optional[float] = None
    limitation: str = (
        "This relationship describes same-window observations and does not "
        "establish causality, persistence, or a future outcome."
    )


def _percent(asset: str, minimum: float = 0.10) -> RequiredObservation:
    return RequiredObservation(asset, "daily_change_pct", "percent", minimum)


RULES: Tuple[CrossAssetRule, ...] = (
    CrossAssetRule(
        rule_id="equity_index_co_movement_v1",
        relationship_kind="co_movement",
        label="SPY and QQQ daily co-movement",
        operator="same_sign",
        required_inputs=(_percent("SPY"), _percent("QQQ")),
    ),
    CrossAssetRule(
        rule_id="crypto_co_movement_v1",
        relationship_kind="co_movement",
        label="BTC-USD and ETH-USD daily co-movement",
        operator="same_sign",
        required_inputs=(_percent("BTC-USD"), _percent("ETH-USD")),
    ),
    CrossAssetRule(
        rule_id="equity_crypto_co_movement_v1",
        relationship_kind="co_movement",
        label="Equity indexes and BTC-USD daily co-movement",
        operator="same_sign",
        required_inputs=(
            _percent("SPY"),
            _percent("QQQ"),
            _percent("BTC-USD"),
        ),
    ),
    CrossAssetRule(
        rule_id="equity_volatility_inverse_move_v1",
        relationship_kind="inverse_movement",
        label="Equity indexes and VIX inverse daily movement",
        operator="equity_pair_inverse_third",
        required_inputs=(_percent("SPY"), _percent("QQQ"), _percent("VIX")),
    ),
    CrossAssetRule(
        rule_id="gold_dollar_inverse_move_v1",
        relationship_kind="inverse_movement",
        label="Gold and DXY inverse daily movement",
        operator="opposite_sign",
        required_inputs=(_percent("GOLD"), _percent("DXY")),
    ),
    CrossAssetRule(
        rule_id="dollar_fx_quote_alignment_v1",
        relationship_kind="quote_alignment",
        label="DXY and major FX quote alignment",
        operator="dollar_fx_quote_alignment",
        required_inputs=(
            _percent("DXY", 0.05),
            _percent("EURUSD", 0.05),
            _percent("USDJPY", 0.05),
        ),
    ),
    CrossAssetRule(
        rule_id="equity_index_divergence_v1",
        relationship_kind="divergence",
        label="SPY and QQQ daily divergence",
        operator="opposite_sign_with_spread",
        required_inputs=(_percent("SPY", 0.0), _percent("QQQ", 0.0)),
        spread_threshold=1.0,
    ),
    CrossAssetRule(
        rule_id="dollar_yield_co_movement_v1",
        relationship_kind="co_movement",
        label="DXY and US10Y daily co-movement",
        operator="same_sign",
        required_inputs=(
            _percent("DXY"),
            RequiredObservation(
                "US10Y",
                "daily_change_bps",
                "basis_points",
                1.0,
            ),
        ),
    ),
)

RULE_BY_ID: Dict[str, CrossAssetRule] = {rule.rule_id: rule for rule in RULES}
