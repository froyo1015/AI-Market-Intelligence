"""Production-safe Gate D projection over already validated artifacts."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

from src.brief.renderer_validator import validate_rendered_brief
from src.consolidation.validator import validate_consolidated_evidence_artifact
from src.data.freshness import validate_freshness_contract
from src.evaluation.minimum_useful_gate import evaluate_gate
from src.intelligence.validator import validate_daily_intelligence_artifact
from src.regime.validator import validate_market_regime_artifact
from src.risk.validator import validate_risk_monitor_artifact
from src.signals.validator import validate_market_signals_artifact
from src.top_intelligence.validator import validate_top_intelligence_artifact


SCHEMA_VERSION = "1.0"
ARTIFACT_TYPE = "minimum_useful_status"
DEFAULT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONTRACT = DEFAULT_ROOT / "minimum-useful-gate-contract.json"
OUTPUT_FIELDS = {
    "schema_version", "artifact_type", "policy_id", "evaluated_at", "status",
    "system_health", "product_usefulness", "overall_status", "minimum_useful",
    "criteria", "asset_class_coverage", "explicit_limitations",
    "provenance_integrity", "freshness_integrity", "source_artifact_references",
    "verified_latest_session_assets_counted",
}


def build_minimum_useful_status(
    artifacts: Mapping[str, Any], contract: Mapping[str, Any],
    *, evaluated_at: str, publication_validated: bool,
) -> dict[str, Any]:
    """Derive Gate D facts without fetching data or mutating source artifacts."""
    required = {
        "market_snapshot", "macro_snapshot", "evidence_bundle", "market_signals",
        "market_regime", "risk_monitor", "daily_intelligence", "top_intelligence",
        "daily_market_brief", "generation_metadata",
    }
    missing = sorted(required - set(artifacts))
    if missing:
        raise ValueError("missing gate input(s): " + ", ".join(missing))
    _timestamp(evaluated_at)
    market, macro = artifacts["market_snapshot"], artifacts["macro_snapshot"]
    bundle, signals = artifacts["evidence_bundle"], artifacts["market_signals"]
    regime, risks = artifacts["market_regime"], artifacts["risk_monitor"]
    daily, top = artifacts["daily_intelligence"], artifacts["top_intelligence"]

    validation_errors = []
    validations = (
        lambda: validate_consolidated_evidence_artifact(bundle),
        lambda: validate_market_signals_artifact(signals, bundle),
        lambda: validate_market_regime_artifact(regime, bundle, signals),
        lambda: validate_risk_monitor_artifact(risks, bundle, signals, regime),
        lambda: validate_daily_intelligence_artifact(daily, bundle, signals, regime, risks),
        lambda: validate_top_intelligence_artifact(top, daily),
        lambda: validate_rendered_brief(artifacts["daily_market_brief"], daily, top),
    )
    for check in validations:
        try:
            check()
        except (ValueError, KeyError, TypeError) as exc:
            validation_errors.append(type(exc).__name__)
    provenance_integrity = not validation_errors

    freshness_errors = []
    for name in ("market_snapshot", "macro_snapshot", "evidence_bundle",
                 "market_signals", "market_regime", "risk_monitor",
                 "daily_intelligence", "top_intelligence"):
        try:
            validate_freshness_contract(artifacts[name])
        except (ValueError, KeyError, TypeError) as exc:
            freshness_errors.append(f"{name}:{type(exc).__name__}")
    freshness_integrity = not freshness_errors

    current_core = _current_records(market)
    current_macro = _current_records(macro)
    current_top = _current_top(top)
    regime_justified = _regime_valid_or_justified(regime)
    risk_substantive = bool(risks.get("risks")) or any(
        "No eligible official events" in str(item) for item in risks.get("warnings", [])
    )
    brief = artifacts["daily_market_brief"]
    brief_substantive = bool(current_top) and all(
        str(item.get("headline")) in brief and str(item.get("why")) in brief
        for item in current_top
    ) and len(brief.strip()) >= 500
    limitations = []
    core_classes = {item["asset_type"] for item in current_core}
    if "equity" not in core_classes:
        limitations.append("equity_core_unavailable")
    if regime.get("classification") is None:
        limitations.append("regime_unavailable")
    if daily.get("status") != "available":
        limitations.append("report_" + str(daily.get("status", "unavailable")))
    if daily.get("freshness_status") != "current":
        limitations.append("report_" + str(daily.get("freshness_status", "unknown")))
    mode = artifacts["generation_metadata"].get("generation_mode", "unavailable")
    if mode != "grounded_ai":
        limitations.append("ai_generation_" + str(mode))
    if validation_errors:
        limitations.append("provenance_validation_failed")
    if freshness_errors:
        limitations.append("freshness_validation_failed")

    snapshot = {
        "snapshot_id": str(daily.get("run_id", "unavailable")),
        "evaluated_at": evaluated_at,
        "current_core_assets": [
            {"symbol": str(item["symbol"]), "asset_class": str(item["asset_type"]),
             "freshness_status": "current"} for item in current_core
        ],
        "current_macro_count": len(current_macro),
        "current_validated_top_count": len(current_top),
        "regime_state": regime.get("classification") or "unavailable",
        "regime_valid_or_justified_unavailable": regime_justified,
        "regime_reason": _regime_reason(regime),
        "risk_monitor_state": str(risks.get("status", "unavailable")),
        "risk_monitor_meaningful_or_explicit_none": risk_substantive,
        "brief_status": str(mode), "brief_substantive": brief_substantive,
        "provenance_integrity": provenance_integrity,
        "freshness_integrity": freshness_integrity,
        "report_status": str(daily.get("status", "unavailable")),
        "report_freshness": str(daily.get("freshness_status", "unknown")),
        "product_limitation_reasons": sorted(set(limitations)),
        "system_checks": {
            "pipeline_completed": True,
            "required_artifacts_generated": True,
            "required_artifacts_validated": provenance_integrity,
            "publication_validated": bool(publication_validated),
            "provenance_integrity": provenance_integrity,
            "freshness_integrity": freshness_integrity,
            "operational_degradation_reasons": [],
        },
    }
    result = evaluate_gate(contract, snapshot)
    output = {
        "schema_version": SCHEMA_VERSION, "artifact_type": ARTIFACT_TYPE,
        "policy_id": result["policy_id"], "evaluated_at": evaluated_at,
        "status": "available" if result["overall_state"] != "unusable" else "unavailable",
        "system_health": result["system_health"],
        "product_usefulness": result["product_usefulness"],
        "overall_status": result["overall_state"],
        "minimum_useful": result["minimum_useful"], "criteria": result["criteria"],
        "asset_class_coverage": result["criteria"]["asset_class_coverage"],
        "explicit_limitations": result["product_usefulness"]["reasons"],
        "provenance_integrity": provenance_integrity,
        "freshness_integrity": freshness_integrity,
        "source_artifact_references": _references(artifacts),
        "verified_latest_session_assets_counted": 0,
    }
    validate_minimum_useful_status(output)
    return output


def validate_minimum_useful_status(payload: Mapping[str, Any]) -> None:
    if set(payload) != OUTPUT_FIELDS or payload.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("minimum useful status fields/version invalid")
    if payload.get("artifact_type") != ARTIFACT_TYPE:
        raise ValueError("minimum useful artifact type invalid")
    _timestamp(payload.get("evaluated_at"))
    if payload.get("status") not in {"available", "unavailable"}:
        raise ValueError("minimum useful artifact status invalid")
    if payload.get("overall_status") not in {"healthy", "degraded", "unusable"}:
        raise ValueError("overall status invalid")
    if not isinstance(payload.get("minimum_useful"), bool):
        raise ValueError("minimum_useful must be boolean")
    if payload.get("verified_latest_session_assets_counted") != 0:
        raise ValueError("unverified session closes cannot count")
    if not isinstance(payload.get("criteria"), dict) or not payload["criteria"]:
        raise ValueError("criteria missing")
    if payload.get("asset_class_coverage") != payload["criteria"].get("asset_class_coverage"):
        raise ValueError("asset class summary mismatch")
    if not isinstance(payload.get("explicit_limitations"), list):
        raise ValueError("limitations invalid")
    if not all(isinstance(value, bool) for value in
               (payload.get("provenance_integrity"), payload.get("freshness_integrity"))):
        raise ValueError("integrity fields invalid")
    refs = payload.get("source_artifact_references")
    if not isinstance(refs, list) or not refs or any(set(ref) != {"artifact", "run_id", "generated_at"} for ref in refs):
        raise ValueError("source artifact references invalid")
    if any(not all(isinstance(value, str) and value for value in ref.values()) for ref in refs):
        raise ValueError("source artifact references incomplete")
    if payload["minimum_useful"] and (not payload["provenance_integrity"] or not payload["freshness_integrity"]):
        raise ValueError("integrity failure cannot be minimum useful")


def run_minimum_useful_status_pipeline(
    paths: Mapping[str, Path], output_path: Path, public_path: Path,
    *, contract_path: Path = DEFAULT_CONTRACT, evaluated_at: str | None = None,
    publication_validated: bool = True,
) -> dict[str, Any]:
    artifacts = {}
    for name, path in paths.items():
        if name == "daily_market_brief":
            artifacts[name] = path.read_text(encoding="utf-8")
        else:
            artifacts[name] = json.loads(path.read_text(encoding="utf-8"))
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    timestamp = evaluated_at or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    output = build_minimum_useful_status(
        artifacts, contract, evaluated_at=timestamp,
        publication_validated=publication_validated,
    )
    _write(output_path, output)
    _write(public_path, output)
    return output


def _current_records(artifact: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    scoped = artifact.get("freshness_items", {}).get("items", {})
    return [item for item in artifact.get("records", [])
            if item.get("status") == "success"
            and scoped.get(str(item.get("symbol")), {}).get("freshness_status") == "current"]


def _current_top(artifact: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    scoped = artifact.get("freshness_items", {}).get("items", {})
    return [item for item in artifact.get("items", [])
            if item.get("validation_status") == "validated"
            and item.get("freshness_status") == "current"
            and scoped.get(str(item.get("item_id")), {}).get("freshness_status") == "current"]


def _regime_valid_or_justified(regime: Mapping[str, Any]) -> bool:
    if regime.get("classification") in {"risk_on", "risk_off", "mixed"}:
        return True
    dimensions = regime.get("dimensions", [])
    return (regime.get("status") == "unavailable" and bool(dimensions)
            and bool(regime.get("warnings"))
            and all(item.get("reason_codes") for item in dimensions))


def _regime_reason(regime: Mapping[str, Any]) -> str:
    if regime.get("classification"):
        return "validated regime classification available"
    return "; ".join(str(item) for item in regime.get("warnings", [])) or "unavailable without justification"


def _references(artifacts: Mapping[str, Any]) -> list[dict[str, str]]:
    refs=[]
    for name in sorted(key for key in artifacts if key not in {"daily_market_brief", "generation_metadata"}):
        item=artifacts[name]
        refs.append({"artifact": name + ".json", "run_id": str(item.get("run_id") or item.get("artifact_type")),
                     "generated_at": str(item.get("generated_at"))})
    return refs


def _timestamp(value: Any) -> None:
    if not isinstance(value, str) or datetime.fromisoformat(value.replace("Z", "+00:00")).tzinfo is None:
        raise ValueError("timezone-aware evaluated_at required")


def _write(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)
