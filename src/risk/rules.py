"""Frozen Phase 6.3-C risk-monitor rule definitions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Tuple


RULE_SET_VERSION = "risk_monitor_rules_v1"
MAXIMUM_INPUT_AGE_HOURS = 24.0
MAXIMUM_FUTURE_SKEW_MINUTES = 5.0
UPCOMING_EVENT_WINDOW_HOURS = 48.0


@dataclass(frozen=True)
class MarketStressRule:
    rule_id: str
    signal_rule_id: str
    evaluator: str
    attention_level: str
    title: str
    description: str


MARKET_STRESS_RULES: Tuple[MarketStressRule, ...] = (
    MarketStressRule(
        rule_id="observed_equity_volatility_stress_v1",
        signal_rule_id="equity_volatility_inverse_move_v1",
        evaluator="equities_lower_vix_higher",
        attention_level="high",
        title="Observed equity and volatility stress",
        description=(
            "Current SPY and QQQ daily changes are negative while the current "
            "VIX daily change is positive."
        ),
    ),
    MarketStressRule(
        rule_id="observed_equity_crypto_stress_v1",
        signal_rule_id="equity_crypto_co_movement_v1",
        evaluator="all_required_lower",
        attention_level="high",
        title="Observed equity and crypto stress",
        description=(
            "Current SPY, QQQ and BTC-USD daily changes are all negative."
        ),
    ),
    MarketStressRule(
        rule_id="observed_equity_divergence_v1",
        signal_rule_id="equity_index_divergence_v1",
        evaluator="condition_observed",
        attention_level="medium",
        title="Observed equity index divergence",
        description="The current SPY and QQQ divergence condition is observed.",
    ),
    MarketStressRule(
        rule_id="observed_dollar_yield_pressure_v1",
        signal_rule_id="dollar_yield_co_movement_v1",
        evaluator="all_required_higher",
        attention_level="medium",
        title="Observed dollar and yield pressure",
        description=(
            "Current DXY daily change and US10Y daily basis-point change are "
            "both positive."
        ),
    ),
)

MARKET_STRESS_BY_ID: Dict[str, MarketStressRule] = {
    rule.rule_id: rule for rule in MARKET_STRESS_RULES
}

DATA_QUALITY_RULE_IDS = {
    "input_coverage_degraded_v1",
    "consolidation_rejections_present_v1",
    "market_signal_coverage_degraded_v1",
    "market_regime_coverage_degraded_v1",
    "input_artifact_stale_v1",
}

ALL_RULE_IDS = (
    {"upcoming_official_event_v1", "observed_risk_off_regime_v1"}
    | DATA_QUALITY_RULE_IDS
    | set(MARKET_STRESS_BY_ID)
)
