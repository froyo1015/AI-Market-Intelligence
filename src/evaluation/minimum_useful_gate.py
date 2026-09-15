"""Audit-only Minimum Useful Intelligence policy evaluator."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping


INTEGRITY_KEYS = ("provenance_integrity", "freshness_integrity")
SYSTEM_REQUIRED = (
    "pipeline_completed", "required_artifacts_generated",
    "required_artifacts_validated", "publication_validated",
    "provenance_integrity", "freshness_integrity",
)


def evaluate_gate(contract: Mapping[str, Any], snapshot: Mapping[str, Any]) -> dict[str, Any]:
    """Evaluate supplied facts; never fetch, publish, or enable production."""
    policy = contract["product_usefulness"]
    useful = policy["useful_requires"]
    degraded = policy["degraded_requires"]
    current_assets = snapshot["current_core_assets"]
    symbols = [item["symbol"] for item in current_assets]
    classes = sorted({item["asset_class"] for item in current_assets})
    risk_classes = sorted(set(classes) & set(useful["risk_asset_classes"]))
    if len(symbols) != len(set(symbols)):
        raise ValueError("current core assets must be distinct")
    if any(item.get("freshness_status") != "current" for item in current_assets):
        raise ValueError("non-current asset supplied as current")

    system_failed = [key for key in SYSTEM_REQUIRED if snapshot["system_checks"].get(key) is not True]
    if system_failed:
        system_state = "unusable"
    elif snapshot["system_checks"].get("operational_degradation_reasons"):
        system_state = "degraded"
    else:
        system_state = "healthy"

    integrity = all(snapshot[key] is True for key in INTEGRITY_KEYS)
    common = {
        "core_count": len(current_assets), "asset_class_count": len(classes),
        "macro_count": snapshot["current_macro_count"],
        "top_count": snapshot["current_validated_top_count"],
        "brief": snapshot["brief_substantive"], "integrity": integrity,
    }
    useful_pass = (
        common["core_count"] >= useful["current_core_asset_count_min"]
        and common["asset_class_count"] >= useful["current_core_asset_class_count_min"]
        and len(risk_classes) >= useful["current_risk_asset_class_count_min"]
        and common["macro_count"] >= useful["current_macro_count_min"]
        and common["top_count"] >= useful["current_validated_top_count_min"]
        and snapshot["regime_valid_or_justified_unavailable"]
        and snapshot["risk_monitor_meaningful_or_explicit_none"]
        and common["brief"] and common["integrity"]
    )
    degraded_pass = (
        common["core_count"] >= degraded["current_core_asset_count_min"]
        and common["asset_class_count"] >= degraded["current_core_asset_class_count_min"]
        and common["macro_count"] >= degraded["current_macro_count_min"]
        and common["top_count"] >= degraded["current_validated_top_count_min"]
        and common["brief"] and common["integrity"]
    )
    product_state = "useful" if useful_pass else "degraded" if degraded_pass else "unusable"
    represented = set(classes)
    missing_classes = sorted(set(contract["declared_core_asset_classes"]) - represented)
    limitation_reasons = list(snapshot["product_limitation_reasons"])
    if missing_classes:
        limitation_reasons.append("missing_current_core_asset_classes:" + ",".join(missing_classes))
    if system_state == "unusable" or product_state == "unusable":
        overall = "unusable"
    elif (system_state != "healthy" or product_state != "useful" or limitation_reasons
          or snapshot["report_status"] != "available"
          or snapshot["report_freshness"] != "current"):
        overall = "degraded"
    else:
        overall = "healthy"

    criteria = {
        "core_asset_coverage": {"passed": common["core_count"] >= useful["current_core_asset_count_min"], "actual": common["core_count"], "required": useful["current_core_asset_count_min"], "symbols": symbols},
        "asset_class_coverage": {"passed": common["asset_class_count"] >= useful["current_core_asset_class_count_min"], "actual": common["asset_class_count"], "required": useful["current_core_asset_class_count_min"], "classes": classes, "missing_declared_classes": missing_classes},
        "risk_asset_class_coverage": {"passed": len(risk_classes) >= useful["current_risk_asset_class_count_min"], "classes": risk_classes},
        "macro_coverage": {"passed": common["macro_count"] >= useful["current_macro_count_min"], "actual": common["macro_count"], "required": useful["current_macro_count_min"]},
        "top_intelligence": {"passed": common["top_count"] >= useful["current_validated_top_count_min"], "actual": common["top_count"], "required": useful["current_validated_top_count_min"]},
        "regime": {"passed": bool(snapshot["regime_valid_or_justified_unavailable"]), "state": snapshot["regime_state"], "reason": snapshot["regime_reason"]},
        "risk_monitor": {"passed": bool(snapshot["risk_monitor_meaningful_or_explicit_none"]), "state": snapshot["risk_monitor_state"]},
        "brief_usefulness": {"passed": bool(common["brief"]), "status": snapshot["brief_status"]},
        "provenance_integrity": {"passed": snapshot["provenance_integrity"] is True},
        "freshness_integrity": {"passed": snapshot["freshness_integrity"] is True},
    }
    return {
        "schema_contract": contract["schema_contract"],
        "policy_id": contract["policy_id"],
        "evaluation_mode": "audit_only",
        "production_enabled": False,
        "snapshot_id": snapshot["snapshot_id"],
        "evaluated_at": snapshot["evaluated_at"],
        "system_health": {"state": system_state, "reasons": sorted(system_failed + list(snapshot["system_checks"].get("operational_degradation_reasons", [])))},
        "product_usefulness": {"state": product_state, "reasons": sorted(set(limitation_reasons))},
        "overall_state": overall,
        "minimum_useful": product_state == "useful" and system_state != "unusable",
        "criteria": criteria,
        "verified_latest_session_assets_counted": 0,
        "input_snapshot": deepcopy(snapshot),
    }
