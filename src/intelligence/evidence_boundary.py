"""Optional versioned evidence context, with no intelligence interpretation."""

import copy
import json
from pathlib import Path

from src.consolidation.validator import validate_consolidated_evidence_artifact
from src.shadow.derivatives.consolidation import compose, validate_bundle
from src.shadow.derivatives.production_validator import milliseconds, unique_pairs, reject_constant
from src.shadow.derivatives.validator import digest

SHADOW_ROOT = Path(__file__).resolve().parents[2] / "outputs/shadow/derivatives"


def read(path):
    payload = json.loads(Path(path).read_text(), object_pairs_hook=unique_pairs, parse_constant=reject_constant)
    if not isinstance(payload, dict):
        raise ValueError("invalid artifact root")
    return payload


def build_context(legacy, bundle, funding_inputs, oi_inputs, as_of):
    validate_consolidated_evidence_artifact(legacy)
    cutoff = milliseconds(as_of)
    result = {"schema_contract": "intelligence_evidence_context_v1", "evaluated_at": as_of,
              "legacy_evidence_ref": {"run_id": legacy["run_id"], "artifact_hash": digest(legacy)},
              "derivatives": {"status": "unavailable", "validation_status": "unavailable", "coverage": [],
                              "records": [], "current_evidence_ids": [], "warnings": []}}
    module = result["derivatives"]
    if bundle is None:
        module["warnings"] = ["derivatives_bundle_missing"]
        return result
    try:
        if cutoff < milliseconds(bundle["evaluation_cutoff"]) or not validate_bundle(bundle, funding_inputs, oi_inputs):
            raise ValueError("invalid derivatives evidence")
        current = compose(funding_inputs, oi_inputs, as_of)
        module.update(status=current["status"], validation_status="validated", coverage=current["coverage"],
                      bundle_ref={"artifact_hash": digest(bundle), "evaluation_cutoff": bundle["evaluation_cutoff"]})
        for fact in current["evidence"]:
            times = [s["observation"] for s in fact["source_records"]]
            eligible = fact["freshness"]["freshness_status"] == "current" and not fact["conflict"] and fact["evidence_quality"]["score"] is not None and fact["evidence_quality"]["score"] > 0
            record = {"id": fact["evidence_id"], "type": "derivatives_observation",
                      "related_assets": [fact["base_asset_id"]], "instrument_id": fact["instrument_id"],
                      "venue_id": fact["venue_id"], "source_records": copy.deepcopy(fact["source_records"]),
                      "observations": [{"metric": fact["metric"], "value": fact["value"], "unit": fact["unit"],
                                        "source_timestamp": fact["source_timestamp"], "observation_refs": fact["observation_refs"]}],
                      "events": [], "evidence_records": [{"claim_type": "measurement_report",
                                                           "metric_definition": fact["metric_definition"]}],
                      "timestamps": {"source_timestamp": fact["source_timestamp"],
                                     "retrieved_at": sorted({o["retrieved_at"] for o in times}),
                                     "generated_at": sorted({o["generated_at"] for o in times}),
                                     "known_at": sorted({o["known_at"] for o in times}), "evaluated_at": as_of},
                      "verification_level": "observed", "validation_status": "validated",
                      "data_quality": {"evidence_quality": fact["evidence_quality"], "conflict": fact["conflict"]},
                      "freshness": fact["freshness"], "current_eligible": eligible,
                      "provenance": {"bundle_ref": module["bundle_ref"], "observation_refs": fact["observation_refs"],
                                     "input_artifacts": current["input_artifacts"], "time_window": fact["time_window"]}}
            module["records"].append(record)
            if eligible:
                module["current_evidence_ids"].append(record["id"])
        if any(not r["current_eligible"] for r in module["records"]):
            module["warnings"].append("derivatives_contains_ineligible_evidence")
    except (ValueError, TypeError, KeyError, IndexError):
        result["derivatives"] = {"status": "unavailable", "validation_status": "invalid", "coverage": [],
                                 "records": [], "current_evidence_ids": [], "warnings": ["derivatives_validation_failed"]}
    return result


def validate_context(context, legacy, bundle, funding_inputs, oi_inputs):
    try:
        return context == build_context(legacy, bundle, funding_inputs, oi_inputs, context["evaluated_at"])
    except (ValueError, TypeError, KeyError):
        return False


def ingest(legacy, bundle_path, funding_paths, oi_paths, as_of):
    try:
        bundle = read(bundle_path)
    except FileNotFoundError:
        return build_context(legacy, None, [], [], as_of)
    except (ValueError, OSError):
        return build_context(legacy, {}, [], [], as_of)
    try:
        inputs = ([read(p) for p in funding_paths], [read(p) for p in oi_paths])
    except (ValueError, OSError):
        return build_context(legacy, {}, [], [], as_of)
    return build_context(legacy, bundle, *inputs, as_of)


def check_output_path(path):
    path = Path(path)
    root = SHADOW_ROOT.absolute()
    resolved = path.resolve()
    if root.resolve() != root or not resolved.is_relative_to(root) or path.absolute() != resolved:
        raise ValueError("context output must stay in shadow namespace")
    return resolved


def write_context(context, path):
    path = check_output_path(path)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    # Exclusive file: no overwrite or collision with existing source artifacts.
    with path.open("x", encoding="utf-8") as stream:
        json.dump(context, stream, sort_keys=True, indent=2)
