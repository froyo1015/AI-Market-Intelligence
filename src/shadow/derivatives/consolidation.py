"""Deterministic, observation-only derivatives evidence in the shadow namespace."""

import argparse
import copy
import json
import os
from dataclasses import dataclass, asdict
from decimal import Decimal

from . import binance_funding as funding
from .production_validator import milliseconds
from .validator import require, digest
from .providers import validate_source, scope


@dataclass(frozen=True)
class DerivativesEvidenceBundle:
    schema_contract: str
    evaluation_cutoff: str
    validation_status: str
    status: str
    freshness_status: str
    coverage: list
    input_artifacts: list
    evidence: list
    groups: list

    def to_dict(self):
        return asdict(self)


def compose(funding_artifacts, oi_artifacts, evaluation_cutoff):
    cutoff = milliseconds(evaluation_cutoff)
    require(isinstance(funding_artifacts, list) and isinstance(oi_artifacts, list), "invalid input lists")
    artifacts, facts = {}, {}
    instruments_scope = scope(funding_artifacts + oi_artifacts)
    for inputs, metric in (
        (funding_artifacts, "funding_rate"), (oi_artifacts, "open_interest"),
    ):
        for a in inputs:
            validate_source(a, metric)
            contract = a["schema_contract"]
            require(milliseconds(a["evaluation_cutoff"]) <= cutoff, "input unavailable at cutoff")
            artifact_id = digest(a)
            if artifact_id in artifacts:
                continue
            artifacts[artifact_id] = {"artifact_hash": artifact_id, "schema_contract": contract,
                                      "provider_id": a["provider_id"], "run_id": a["run_id"],
                                      "evaluation_cutoff": a["evaluation_cutoff"]}
            output = a["observation_output"]
            instruments = {i["instrument_id"] + "@" + str(i["version"]): i for i in output["instruments"]}
            for o in output["observations"]:
                instrument = instruments[o["instrument_ref"]]
                d = instrument["definition"]
                identity = {key: d[key] for key in ("venue_id", "base_asset_id", "quote_asset_id",
                                                   "settlement_asset_id", "underlying_asset_id")}
                identity["instrument_id"] = instrument["instrument_id"]
                day = o["source_timestamp"][:10]
                definition_keys = ("funding_interval_seconds", "funding_rate_kind", "funding_sign_convention") if o["metric"] == "funding_rate" else ("oi_unit", "counting_basis")
                definition = {key: d[key] for key in definition_keys}
                fact_key = {**identity, "metric": o["metric"], "value": o["value"], "unit": o["unit"],
                            "source_timestamp": o["source_timestamp"], "metric_definition": definition}
                key = digest(fact_key)
                if key not in facts:
                    facts[key] = {"evidence_id": "evidence:" + key[7:], "claim_type": "measurement_report",
                                  **fact_key, "time_window": {"utc_day": day},
                                  "observation_refs": [], "source_records": []}
                fact = facts[key]
                ref = artifact_id + "/" + o["observation_id"] + "@" + str(o["version"])
                bridges = [b for b in a["normalization_receipts"] if b["normalized_receipt_ref"] in
                           (o["receipt_ref"], instrument["metadata_receipt_ref"])]
                names = sorted({name for b in bridges for name in b["capture_refs"]})
                fact["observation_refs"].append(ref)
                fact["source_records"].append({"observation_ref": ref, "artifact_hash": artifact_id,
                    "observation": copy.deepcopy(o), "instrument_revision": copy.deepcopy(instrument),
                    "normalization_receipts": copy.deepcopy(bridges),
                    "captures": {name: {k: v for k, v in a["captures"][name].items() if k != "body_base64"} for name in names},
                    "receipts": [copy.deepcopy(r) for r in output["receipts"] if r["receipt_id"] in
                                 (o["receipt_ref"], instrument["metadata_receipt_ref"])]})
    evidence = sorted(facts.values(), key=lambda f: f["evidence_id"])
    groups, conflicts = {}, {}
    for fact in evidence:
        fact["observation_refs"].sort()
        fact["source_records"].sort(key=lambda r: r["observation_ref"])
        age = Decimal(cutoff - milliseconds(fact["source_timestamp"])) / 1000
        ttl = fact["metric_definition"]["funding_interval_seconds"] + 1800 if fact["metric"] == "funding_rate" else 7200
        current = age <= ttl
        scores = [r["observation"]["evidence_quality"]["score"] for r in fact["source_records"]]
        score = None if None in scores else min(*scores, int(current))
        fact["freshness"] = {"evaluated_at": evaluation_cutoff, "source_timestamp": fact["source_timestamp"],
                             "age_seconds": funding.canonical(format(age, "f")), "freshness_status": "current" if current else "stale"}
        fact["evidence_quality"] = {"policy_id": "derivatives-consolidation-quality-v1",
                                    "input_scores": scores, "timeliness": int(current), "score": score}
        identity = {k: fact[k] for k in ("instrument_id", "venue_id", "base_asset_id", "quote_asset_id",
                                       "settlement_asset_id", "underlying_asset_id")}
        gkey = digest({**identity, "window": fact["time_window"]})
        group = groups.setdefault(gkey, {"group_id": "group:" + gkey[7:], **identity,
                                        "time_window": fact["time_window"], "evidence_refs": [], "source_timestamps": []})
        group["evidence_refs"].append(fact["evidence_id"])
        group["source_timestamps"].append(fact["source_timestamp"])
        ckey = digest({**identity, "metric": fact["metric"], "timestamp": fact["source_timestamp"]})
        conflicts.setdefault(ckey, []).append(fact)
    for same in conflicts.values():
        for fact in same:
            fact["conflict"] = len(same) > 1
    for group in groups.values():
        group["evidence_refs"].sort()
        group["source_timestamps"] = sorted(set(group["source_timestamps"]))
        times = group["source_timestamps"]
        group["observed_range"] = {"start": times[0], "end": times[-1]}
        group["timestamp_skew_ms"] = milliseconds(times[-1]) - milliseconds(times[0])
        group["simultaneous"] = len(times) == 1
    coverage = []
    for symbol, instrument_id in instruments_scope.items():
        for metric in ("funding_rate", "open_interest"):
            selected = [f for f in evidence if f["instrument_id"] == instrument_id and f["metric"] == metric]
            coverage.append({"symbol": symbol, "metric": metric, "status": "available" if selected else "unavailable",
                             "fact_count": len(selected), "current_count": sum(f["freshness"]["freshness_status"] == "current" for f in selected)})
    n = sum(c["status"] == "available" for c in coverage)
    fresh = {f["freshness"]["freshness_status"] for f in evidence}
    return DerivativesEvidenceBundle("derivatives_evidence_bundle_v1", evaluation_cutoff, "validated",
        "available" if n == 4 else "partial" if n else "unavailable",
        "unavailable" if not fresh else next(iter(fresh)) if len(fresh) == 1 else "unknown",
        coverage, [artifacts[k] for k in sorted(artifacts)], evidence, [groups[k] for k in sorted(groups)]).to_dict()


def validate_bundle(bundle, funding_artifacts, oi_artifacts):
    try:
        return bundle == compose(funding_artifacts, oi_artifacts, bundle["evaluation_cutoff"])
    except (ValueError, TypeError, KeyError):
        return False


def main():
    parser = argparse.ArgumentParser(description="Shadow derivatives fact consolidation only")
    parser.add_argument("--funding", action="append", default=[])
    parser.add_argument("--oi", action="append", default=[])
    parser.add_argument("--as-of", required=True)
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    from pathlib import Path
    import re
    require(re.fullmatch(r"[A-Za-z0-9_-]+", args.run_id), "unsafe run ID")
    load = lambda paths: [json.loads(Path(p).read_text()) for p in paths]
    bundle = compose(load(args.funding), load(args.oi), args.as_of)
    root = funding.ROOT.resolve()
    require(root == funding.ROOT.absolute() and not funding.ROOT.is_symlink(), "unsafe shadow root")
    root.mkdir(parents=True, exist_ok=True)
    target = root / args.run_id
    target.mkdir(mode=0o700, exist_ok=False)
    pending = target / "pending.json"
    with pending.open("x") as stream:
        json.dump(bundle, stream, indent=2, sort_keys=True)
        stream.flush()
        os.fsync(stream.fileno())
    pending.replace(target / "derivatives_evidence_bundle.json")
    print(bundle["status"])


if __name__ == "__main__":
    main()
