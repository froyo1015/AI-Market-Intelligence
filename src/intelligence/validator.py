"""Validation for Phase 6.4-A structured daily intelligence."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Mapping

from src.data.freshness import strip_freshness_metadata, validate_freshness_contract
from src.intelligence.composer import build_daily_intelligence_artifact


PROHIBITED_KEYS = {
    "bearish",
    "bullish",
    "forecast",
    "llm",
    "market_prediction",
    "natural_language_analysis",
    "opinion",
    "prediction",
    "price_target",
    "rank",
    "ranking",
    "recommendation",
    "sentiment",
    "target_price",
    "trade_action",
    "trading_recommendation",
    "trading_signal",
}


class DailyIntelligenceValidationError(ValueError):
    """Raised when daily_intelligence.json violates its frozen contract."""


def validate_daily_intelligence_artifact(
    artifact: Mapping[str, Any],
    evidence_bundle: Mapping[str, Any],
    market_signals: Mapping[str, Any],
    market_regime: Mapping[str, Any],
    risk_monitor: Mapping[str, Any],
) -> None:
    if "freshness_contract_version" in artifact:
        validate_freshness_contract(artifact)
    from src.data.item_freshness import validate_scoped_evidence
    validate_scoped_evidence(artifact, (evidence_bundle, market_signals, market_regime, risk_monitor))
    domain_artifact = strip_freshness_metadata(artifact)
    _scan_keys(domain_artifact)
    generated_at = artifact.get("generated_at")
    if not isinstance(generated_at, str):
        raise DailyIntelligenceValidationError("generated_at must be a timestamp")
    try:
        generated = datetime.fromisoformat(generated_at.replace("Z", "+00:00"))
    except ValueError as exc:
        raise DailyIntelligenceValidationError("generated_at is invalid") from exc
    if generated.tzinfo is None:
        raise DailyIntelligenceValidationError("generated_at must include timezone")
    expected = build_daily_intelligence_artifact(
        evidence_bundle,
        market_signals,
        market_regime,
        risk_monitor,
        now=generated,
    ).to_dict()
    if domain_artifact != expected:
        raise DailyIntelligenceValidationError(
            "daily-intelligence artifact does not match deterministic assembly"
        )


def _scan_keys(value: Any, context: str = "artifact") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if str(key).casefold() in PROHIBITED_KEYS:
                raise DailyIntelligenceValidationError(
                    f"prohibited Phase 6.4-A field: {key}"
                )
            _scan_keys(child, f"{context}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _scan_keys(child, f"{context}[{index}]")
