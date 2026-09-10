"""Read-only daily context wrapper; never changes canonical writer inputs."""

import copy

from src.intelligence.evidence_boundary import build_context, read
from src.intelligence.validator import validate_daily_intelligence_artifact


def build_daily_context(daily, legacy, signals, regime, risk, bundle, funding_inputs, oi_inputs, as_of):
    validate_daily_intelligence_artifact(daily, legacy, signals, regime, risk)
    boundary = build_context(legacy, bundle, funding_inputs, oi_inputs, as_of)
    module = boundary["derivatives"]
    return {"schema_contract": "daily_intelligence_context_v1",
            "daily_intelligence": copy.deepcopy(daily),
            "derivatives_evidence": {
                "scope": "read_only_facts", "status": module["status"],
                "validation_status": module["validation_status"], "evaluated_at": as_of,
                "coverage": copy.deepcopy(module["coverage"]),
                "current_facts": [copy.deepcopy(r) for r in module["records"] if r["current_eligible"]],
                "excluded_evidence_refs": [r["id"] for r in module["records"] if not r["current_eligible"]],
                "bundle_ref": copy.deepcopy(module.get("bundle_ref")),
                "warnings": list(module["warnings"])}}


def validate_daily_context(context, legacy, signals, regime, risk, bundle, funding_inputs, oi_inputs):
    try:
        return context == build_daily_context(context["daily_intelligence"], legacy, signals, regime, risk,
                                              bundle, funding_inputs, oi_inputs, context["derivatives_evidence"]["evaluated_at"])
    except (ValueError, KeyError, TypeError):
        return False


def load_daily_context(daily, legacy, signals, regime, risk, bundle_path, funding_paths, oi_paths, as_of):
    try:
        bundle = read(bundle_path)
    except FileNotFoundError:
        bundle = None
    except (OSError, ValueError):
        bundle = {}
    try:
        funding_inputs, oi_inputs = [read(p) for p in funding_paths], [read(p) for p in oi_paths]
    except (OSError, ValueError):
        bundle, funding_inputs, oi_inputs = {}, [], []
    return build_daily_context(daily, legacy, signals, regime, risk, bundle, funding_inputs, oi_inputs, as_of)
