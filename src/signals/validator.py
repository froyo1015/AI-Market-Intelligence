"""Validation for deterministic Phase 6.3-A relationship signals."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Mapping

from src.consolidation.validator import validate_consolidated_evidence_artifact
from src.data.freshness import (
    strip_freshness_metadata,
    validate_freshness_contract,
)
from src.signals.engine import build_market_signals_artifact


PROHIBITED_KEYS = {
    "bearish",
    "bullish",
    "direction",
    "forecast",
    "market_prediction",
    "prediction",
    "price_target",
    "rank",
    "ranking",
    "recommendation",
    "regime",
    "sentiment",
    "strength",
    "target_price",
    "trade",
    "trading_action",
    "trading_signal",
}
PROHIBITED_VALUES = re.compile(
    r"\b(?:bullish|bearish|risk_on|risk_off|buy|sell|forecast|prediction|"
    r"price target|trade recommendation)\b|看漲|看跌|買入|賣出|預測",
    re.IGNORECASE,
)
CAUSAL_LANGUAGE = re.compile(
    r"\b(?:because|because of|caused|causes|due to|led to|driven by)\b|"
    r"因為|由於|導致|造成|驅動",
    re.IGNORECASE,
)


class MarketSignalsValidationError(ValueError):
    """Raised when market_signals.json violates the frozen rule contract."""


def validate_market_signals_artifact(
    artifact: Mapping[str, Any],
    evidence_bundle: Mapping[str, Any],
) -> None:
    validate_consolidated_evidence_artifact(evidence_bundle)
    if "freshness_contract_version" in artifact:
        validate_freshness_contract(artifact)
    from src.data.item_freshness import validate_scoped_evidence
    validate_scoped_evidence(artifact, (evidence_bundle,))
    domain_artifact = strip_freshness_metadata(artifact)
    _scan_output(domain_artifact)
    generated_at = artifact.get("generated_at")
    if not isinstance(generated_at, str):
        raise MarketSignalsValidationError("generated_at must be a timestamp")
    try:
        generated = datetime.fromisoformat(generated_at.replace("Z", "+00:00"))
    except ValueError as exc:
        raise MarketSignalsValidationError("generated_at is invalid") from exc
    if generated.tzinfo is None:
        raise MarketSignalsValidationError("generated_at must include timezone")
    expected = build_market_signals_artifact(
        evidence_bundle,
        now=generated,
    ).to_dict()
    if domain_artifact != expected:
        raise MarketSignalsValidationError(
            "signal artifact does not match deterministic rule evaluation"
        )


def _scan_output(value: Any, context: str = "artifact") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            normalized_key = str(key).casefold()
            if normalized_key in PROHIBITED_KEYS:
                raise MarketSignalsValidationError(
                    f"prohibited Phase 6.3-A field: {key}"
                )
            _scan_output(child, f"{context}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _scan_output(child, f"{context}[{index}]")
    elif isinstance(value, str):
        if PROHIBITED_VALUES.search(value):
            raise MarketSignalsValidationError(
                f"{context} contains a prohibited directional or trading label"
            )
        if CAUSAL_LANGUAGE.search(value):
            raise MarketSignalsValidationError(
                f"{context} contains prohibited causal language"
            )
