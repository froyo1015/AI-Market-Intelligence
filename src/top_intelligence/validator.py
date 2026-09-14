"""Validation for deterministic Top Market Intelligence artifacts."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Mapping

from src.data.freshness import strip_freshness_metadata, validate_freshness_contract
from src.top_intelligence.selector import build_top_intelligence_artifact


PROHIBITED_KEYS = {
    "bullish", "bearish", "forecast", "prediction", "price_target",
    "recommendation", "sentiment", "trade_action", "trading_signal", "llm",
}
PROHIBITED_PHRASES = (" buy ", " sell ", " will rise", " will fall", " caused ")


class TopIntelligenceValidationError(ValueError):
    """Raised when top_intelligence.json violates its frozen contract."""


def validate_top_intelligence_artifact(
    artifact: Mapping[str, Any], daily: Mapping[str, Any]
) -> None:
    if "freshness_contract_version" in artifact:
        validate_freshness_contract(artifact)
    if "freshness_items" in artifact:
        from src.data.item_freshness import build_item_freshness
        if artifact["freshness_items"] != build_item_freshness(strip_freshness_metadata(artifact), (daily,)):
            raise TopIntelligenceValidationError("item freshness does not match referenced evidence")
    domain = strip_freshness_metadata(artifact)
    _scan(domain)
    generated_at = domain.get("generated_at")
    if not isinstance(generated_at, str):
        raise TopIntelligenceValidationError("generated_at must be a timestamp")
    try:
        generated = datetime.fromisoformat(generated_at.replace("Z", "+00:00"))
    except ValueError as exc:
        raise TopIntelligenceValidationError("generated_at is invalid") from exc
    if generated.tzinfo is None:
        raise TopIntelligenceValidationError("generated_at must include timezone")
    expected = build_top_intelligence_artifact(daily, now=generated).to_dict()
    if domain != expected:
        raise TopIntelligenceValidationError(
            "top-intelligence artifact does not match deterministic selection"
        )


def _scan(value: Any) -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            if str(key).casefold() in PROHIBITED_KEYS:
                raise TopIntelligenceValidationError(f"prohibited field: {key}")
            _scan(child)
    elif isinstance(value, list):
        for child in value:
            _scan(child)
    elif isinstance(value, str):
        padded = f" {value.casefold()} "
        if any(phrase in padded for phrase in PROHIBITED_PHRASES):
            raise TopIntelligenceValidationError("prohibited predictive or trading phrase")
