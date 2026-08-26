"""Frozen Phase 6.3-B market regime rule registry."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Tuple


RULE_SET_VERSION = "market_regime_rules_v1"
MAXIMUM_INPUT_AGE_HOURS = 24.0
MAXIMUM_FUTURE_SKEW_MINUTES = 5.0
MINIMUM_ELIGIBLE_WEIGHT = 0.65
MINIMUM_ELIGIBLE_DIMENSIONS = 3
RISK_ON_THRESHOLD = 0.25
RISK_OFF_THRESHOLD = -0.25
ANCHOR_DIMENSIONS = {"equity", "volatility"}


@dataclass(frozen=True)
class RegimeDimensionRule:
    dimension_id: str
    weight: float
    signal_rule_id: str
    evaluator: str
    required_assets: Tuple[str, ...]


DIMENSION_RULES: Tuple[RegimeDimensionRule, ...] = (
    RegimeDimensionRule(
        dimension_id="equity",
        weight=0.30,
        signal_rule_id="equity_index_co_movement_v1",
        evaluator="aligned_risk_assets",
        required_assets=("SPY", "QQQ"),
    ),
    RegimeDimensionRule(
        dimension_id="volatility",
        weight=0.25,
        signal_rule_id="equity_volatility_inverse_move_v1",
        evaluator="inverse_volatility",
        required_assets=("VIX",),
    ),
    RegimeDimensionRule(
        dimension_id="crypto",
        weight=0.20,
        signal_rule_id="crypto_co_movement_v1",
        evaluator="aligned_risk_assets",
        required_assets=("BTC-USD", "ETH-USD"),
    ),
    RegimeDimensionRule(
        dimension_id="dollar_yield",
        weight=0.15,
        signal_rule_id="dollar_yield_co_movement_v1",
        evaluator="inverse_pressure_pair",
        required_assets=("DXY", "US10Y"),
    ),
    RegimeDimensionRule(
        dimension_id="cross_asset_alignment",
        weight=0.10,
        signal_rule_id="equity_crypto_co_movement_v1",
        evaluator="aligned_risk_assets",
        required_assets=("SPY", "QQQ", "BTC-USD"),
    ),
)

DIMENSION_BY_ID: Dict[str, RegimeDimensionRule] = {
    rule.dimension_id: rule for rule in DIMENSION_RULES
}
