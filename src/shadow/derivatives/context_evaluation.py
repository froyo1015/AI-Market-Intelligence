"""Offline shadow-only consistency/coverage metrics; no market assessment."""

import argparse
import re
from decimal import Decimal

from src.intelligence.evidence_boundary import read, write_context
from .production_validator import milliseconds, content_hash
from .validator import digest, require, fraction
from .binance_funding import canonical

SLOTS = {(f"instrument:binance-usdm-{symbol}", metric)
         for symbol in ("btcusdt", "ethusdt") for metric in ("funding_rate", "open_interest")}


def ratio(numerator, denominator):
    return {"numerator": numerator, "denominator": denominator,
            "value": numerator / denominator if denominator else None}


def _hash(value):
    require(isinstance(value, str) and re.fullmatch(r"sha256:[0-9a-f]{64}", value), "invalid hash")


def _provenance(fact, bundle, cutoff):
    sources = fact["source_records"]
    require(bool(sources), "missing sources")
    refs = [s["observation_ref"] for s in sources]
    require(sorted(refs) == fact["observation_refs"] and len(set(refs)) == len(refs), "source references")
    artifacts = {a["artifact_hash"] for a in bundle["input_artifacts"]}
    scores = []
    for source in sources:
        o, i = source["observation"], source["instrument_revision"]
        require(o["content_hash"] == content_hash(o) and i["content_hash"] == content_hash(i), "record hash")
        require(source["artifact_hash"] in artifacts, "artifact reference")
        require(source["observation_ref"] == source["artifact_hash"] + "/" + o["observation_id"] + "@" + str(o["version"]), "observation reference")
        require(o["instrument_ref"] == i["instrument_id"] + "@" + str(i["version"]), "instrument revision")
        require(i["instrument_id"] == fact["instrument_id"], "instrument identity")
        require(all(i["definition"][k] == v for k, v in fact["metric_definition"].items()), "metric definition")
        for key in ("venue_id", "base_asset_id", "quote_asset_id", "settlement_asset_id", "underlying_asset_id"):
            require(i["definition"][key] == fact[key], "identity")
        for key in ("metric", "value", "unit", "source_timestamp"):
            require(o[key] == fact[key], "observation mismatch")
        require(o["synthetic"] is False, "synthetic observation")
        for key in ("source_timestamp", "retrieved_at", "generated_at", "known_at"):
            require(milliseconds(o[key]) <= cutoff, "future record")
        receipts = {r["receipt_id"]: r for r in source["receipts"]}
        required = {o["receipt_ref"], i["metadata_receipt_ref"]}
        require(required == set(receipts), "receipt links")
        for r in receipts.values():
            _hash(r["sha256"])
            require(bool(r["source_id"]), "missing source ID")
            milliseconds(r["captured_at"])
        bridges = source["normalization_receipts"]
        require({b["normalized_receipt_ref"] for b in bridges} == required, "normalization links")
        for b in bridges:
            require(bool(b["capture_refs"]), "missing captures")
            require(b["capture_hashes"] == [source["captures"][n]["sha256"] for n in b["capture_refs"]], "capture hashes")
            for h in b["capture_hashes"]:
                _hash(h)
        score = o["evidence_quality"]["score"]
        fraction(score)
        scores.append(score)
    return scores


def _metrics(bundle, context):
    require(context["schema_contract"] == "daily_intelligence_context_v1", "context contract")
    section = context["derivatives_evidence"]
    require(section["scope"] == "read_only_facts", "context scope")
    cutoff = milliseconds(section["evaluated_at"])
    if bundle is None:
        require(section["status"] == "unavailable" and not section["current_facts"]
                and not section["excluded_evidence_refs"] and section["bundle_ref"] is None, "missing bundle mismatch")
        facts = []
    else:
        require(bundle["schema_contract"] == "derivatives_evidence_bundle_v1"
                and bundle["validation_status"] == "validated"
                and section["validation_status"] == "validated", "unvalidated inputs")
        require(milliseconds(bundle["evaluation_cutoff"]) <= cutoff, "future bundle")
        require(section["bundle_ref"] == {"artifact_hash": digest(bundle), "evaluation_cutoff": bundle["evaluation_cutoff"]}, "bundle reference")
        facts = bundle["evidence"]
    ids = [f["evidence_id"] for f in facts]
    require(len(ids) == len(set(ids)), "duplicate evidence")
    current = section["current_facts"]
    actual = {r["id"]: r for r in current}
    require(len(actual) == len(current), "duplicate current fact")
    excluded, expected, slots, scores = [], set(), set(), []
    fresh_count = 0
    for fact in facts:
        identity = {k: fact[k] for k in ("venue_id", "base_asset_id", "quote_asset_id",
            "settlement_asset_id", "underlying_asset_id", "instrument_id", "metric", "value",
            "unit", "source_timestamp", "metric_definition")}
        require(fact["evidence_id"] == "evidence:" + digest(identity)[7:], "evidence identity")
        slot = (fact["instrument_id"], fact["metric"])
        require(slot in SLOTS, "unsupported slot")
        slots.add(slot)
        source_scores = _provenance(fact, bundle, cutoff)
        age = Decimal(cutoff - milliseconds(fact["source_timestamp"])) / 1000
        ttl = fact["metric_definition"]["funding_interval_seconds"] + 1800 if fact["metric"] == "funding_rate" else 7200
        fresh = age <= ttl
        fresh_count += int(fresh)
        score = None if None in source_scores else min(*source_scores, int(fresh))
        scores.append(score)
        eligible = fresh and not fact["conflict"] and score is not None and score > 0
        if not eligible:
            excluded.append(fact["evidence_id"])
            continue
        expected.add(fact["evidence_id"])
        r = actual[fact["evidence_id"]]
        require(r["source_records"] == fact["source_records"], "source preservation")
        require(r["related_assets"] == [fact["base_asset_id"]] and r["instrument_id"] == fact["instrument_id"]
                and r["venue_id"] == fact["venue_id"], "context identity")
        require(r["observations"] == [{k: fact[k] for k in ("metric", "value", "unit", "source_timestamp", "observation_refs")}], "context observations")
        require(r["provenance"] == {"bundle_ref": section["bundle_ref"], "observation_refs": fact["observation_refs"],
                "input_artifacts": bundle["input_artifacts"], "time_window": fact["time_window"]}, "context provenance")
        times = [s["observation"] for s in fact["source_records"]]
        require(r["timestamps"] == {"source_timestamp": fact["source_timestamp"], "evaluated_at": section["evaluated_at"],
                **{k: sorted({o[k] for o in times}) for k in ("retrieved_at", "generated_at", "known_at")}}, "context timestamps")
        require(r["freshness"] == {"evaluated_at": section["evaluated_at"], "source_timestamp": fact["source_timestamp"],
                "age_seconds": canonical(format(age, "f")), "freshness_status": "current"}, "context freshness")
        require(r["data_quality"] == {"conflict": fact["conflict"], "evidence_quality": {
            "policy_id": "derivatives-consolidation-quality-v1", "input_scores": source_scores,
            "timeliness": int(fresh), "score": score}}, "context quality")
        require(r["current_eligible"] is True and r["validation_status"] == "validated", "eligibility")
    require(set(actual) == expected and sorted(section["excluded_evidence_refs"]) == sorted(excluded), "evidence partition")
    status = "available" if len(slots) == 4 else "partial" if slots else "unavailable"
    require(section["status"] == status, "availability mismatch")
    known = [s for s in scores if s is not None]
    n = len(facts)
    return status, {"data_availability": ratio(len(slots), 4),
        "freshness_success_rate": ratio(fresh_count, n),
        "evidence_quality": {"mean_known_score": sum(known) / len(known) if known else None,
                             "known_count": len(known), "unknown_count": n - len(known)},
        "provenance_completeness": ratio(n, n),
        "current_vs_stale": {"current": ratio(fresh_count, n), "stale": ratio(n - fresh_count, n)},
        "missing_data_frequency": {**ratio(4 - len(slots), 4), "sample_count": 1, "scope": "snapshot_slots"}}


def evaluate(bundle, context):
    result = {"schema_contract": "derivatives_context_evaluation_v1", "evaluated_at": None,
              "input_hashes": {}, "validation_status": "invalid", "status": "unavailable",
              "metrics": None, "evidence_refs": [], "errors": []}
    try:
        result["input_hashes"] = {"bundle": digest(bundle) if bundle is not None else None, "context": digest(context)}
        cutoff = context["derivatives_evidence"]["evaluated_at"]
        milliseconds(cutoff)
        result["evaluated_at"] = cutoff
        status, metrics = _metrics(bundle, context)
        result.update(validation_status="validated", status=status, metrics=metrics,
                      evidence_refs=sorted(f["evidence_id"] for f in bundle["evidence"]) if bundle else [])
    except (ValueError, TypeError, KeyError, IndexError, ArithmeticError):
        result["errors"] = ["input_consistency_failed"]
    return result


def validate_evaluation(result, bundle, context):
    return result == evaluate(bundle, context)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", required=True)
    parser.add_argument("--context", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    def load(path):
        try:
            return read(path)
        except FileNotFoundError:
            return None
        except (ValueError, OSError):
            return {}
    write_context(evaluate(load(args.bundle), load(args.context)), args.output)


if __name__ == "__main__":
    main()
