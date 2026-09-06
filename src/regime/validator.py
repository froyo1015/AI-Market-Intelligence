"""Validation for Phase 6.3-B current-condition regime artifacts."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Mapping

from src.data.freshness import strip_freshness_metadata, validate_freshness_contract
from src.regime.classifier import build_market_regime_artifact


PROHIBITED_KEYS = {
    "action",
    "bullish",
    "bearish",
    "expected_return",
    "forecast",
    "future_direction",
    "prediction",
    "price_target",
    "probability",
    "recommendation",
    "sentiment",
    "target_price",
    "trade",
    "trading_action",
    "trading_signal",
}
PROHIBITED_LANGUAGE = re.compile(
    r"\b(?:bullish|bearish|buy|sell|forecast|predict(?:ion|s|ed)?|"
    r"price target|expected return|trade recommendation)\b|"
    r"看漲|看跌|買入|賣出|預測|目標價",
    re.IGNORECASE,
)
CAUSAL_LANGUAGE = re.compile(
    r"\b(?:because|because of|caused|causes|due to|led to|driven by)\b|"
    r"因為|由於|導致|造成|驅動",
    re.IGNORECASE,
)


class MarketRegimeValidationError(ValueError):
    """Raised when market_regime.json violates its frozen contract."""


def validate_market_regime_artifact(
    artifact: Mapping[str, Any],
    evidence_bundle: Mapping[str, Any],
    market_signals: Mapping[str, Any],
) -> None:
    if "freshness_contract_version" in artifact:
        validate_freshness_contract(artifact)
    domain_artifact = strip_freshness_metadata(artifact)
    _scan_output(domain_artifact)
    generated_at = artifact.get("generated_at")
    if not isinstance(generated_at, str):
        raise MarketRegimeValidationError("generated_at must be a timestamp")
    try:
        generated = datetime.fromisoformat(generated_at.replace("Z", "+00:00"))
    except ValueError as exc:
        raise MarketRegimeValidationError("generated_at is invalid") from exc
    if generated.tzinfo is None:
        raise MarketRegimeValidationError("generated_at must include timezone")
    expected = build_market_regime_artifact(
        evidence_bundle,
        market_signals,
        now=generated,
    ).to_dict()
    if domain_artifact != expected:
        raise MarketRegimeValidationError(
            "regime artifact does not match deterministic classification"
        )


def _scan_output(value: Any, context: str = "artifact") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if str(key).casefold() in PROHIBITED_KEYS:
                raise MarketRegimeValidationError(
                    f"prohibited Phase 6.3-B field: {key}"
                )
            _scan_output(child, f"{context}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _scan_output(child, f"{context}[{index}]")
    elif isinstance(value, str):
        if PROHIBITED_LANGUAGE.search(value):
            raise MarketRegimeValidationError(
                f"{context} contains predictive or trading language"
            )
        if CAUSAL_LANGUAGE.search(value):
            raise MarketRegimeValidationError(
                f"{context} contains prohibited causal language"
            )
