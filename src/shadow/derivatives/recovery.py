"""Rights-closed operational proof; never a public market-data projection."""

import copy
import re

from src.pages.derivatives_schema import validate_public
from .production_validator import milliseconds
from .provider_security import FailureCode
from .providers import VENUES, validate_source
from .validator import require


def withhold_metrics(public):
    result = copy.deepcopy(public)
    for row in result["measurements"]:
        row.update(value=None, source_timestamp=None, freshness_status="unavailable",
                   evidence_quality=None, provenance_status="unavailable")
    result["validation_status"] = "unavailable"
    require(validate_public(result), "invalid rights-closed projection")
    return result


def proof(wrappers, before, after, facts, generated_at):
    rows = []
    for a, metric in zip(wrappers, ("funding_rate", "open_interest")):
        validate_source(a, metric)
        output = a["observation_output"]
        instruments = {i["instrument_id"] + "@" + str(i["version"]): i for i in output["instruments"]}
        for symbol, iid in VENUES[a["provider_id"]].items():
            matches = [o for o in output["observations"] if o["metric"] == metric and
                       o["instrument_ref"].split("@")[0] == iid]
            o = matches[0] if matches else None
            failure = a["failures"].get(symbol)
            row = {"provider": a["provider_id"], "instrument_id": iid, "symbol": symbol,
                   "metric": metric, "status": "available" if o else "unavailable",
                   "failure_code": failure, "http_status": 200 if o else None,
                   "api_status": "0" if o and a["provider_id"] == "okx" else None,
                   "source_timestamp": o["source_timestamp"] if o else None,
                   "retrieved_at": o["retrieved_at"] if o else None,
                   "freshness": o["freshness"]["freshness_status"] if o else "unavailable",
                   "unit": o["unit"] if o else None,
                   "funding_interval_seconds": instruments[o["instrument_ref"]]["definition"]["funding_interval_seconds"] if o else None,
                   "provenance_validated": bool(o), "receipt_integrity_validated": bool(o)}
            rows.append(row)
    result = {"schema_contract": "derivatives_recovery_proof_v1", "generated_at": generated_at,
              "production_enabled": False, "public_metrics_enabled": False,
              "rights_status": "blocked", "observations": rows,
              "archive": {"before_entry_hashes": sorted(before), "after_entry_hashes": sorted(after),
                          "prior_entries_preserved": set(before) <= set(after),
                          "distinct_fact_count": len(facts["facts"]),
                          "fact_ids": [f["evidence_id"] for f in facts["facts"]]}}
    validate_proof(result)
    return result


def validate_proof(p):
    require(set(p) == {"schema_contract", "generated_at", "production_enabled", "public_metrics_enabled",
                       "rights_status", "observations", "archive"}, "unsafe recovery proof fields")
    require(p["schema_contract"] == "derivatives_recovery_proof_v1" and p["production_enabled"] is False
            and p["public_metrics_enabled"] is False and p["rights_status"] == "blocked", "unsafe recovery mode")
    cutoff = milliseconds(p["generated_at"])
    require(isinstance(p["observations"], list) and len(p["observations"]) == 4, "invalid proof coverage")
    seen, providers = set(), set()
    keys = set("provider instrument_id symbol metric status failure_code http_status api_status source_timestamp retrieved_at freshness unit funding_interval_seconds provenance_validated receipt_integrity_validated".split())
    for r in p["observations"]:
        require(set(r) == keys and r["provider"] in VENUES, "unsafe proof row")
        require(VENUES[r["provider"]].get(r["symbol"]) == r["instrument_id"], "proof identity")
        require(r["metric"] in ("funding_rate", "open_interest"), "invalid proof metric")
        seen.add((r["instrument_id"], r["metric"]))
        providers.add(r["provider"])
        require(r["failure_code"] is None or r["failure_code"] in {f.value for f in FailureCode}, "unsafe failure")
        if r["status"] == "available":
            require(r["http_status"] == 200 and r["failure_code"] is None and
                    r["api_status"] == ("0" if r["provider"] == "okx" else None), "proof success mismatch")
            require(milliseconds(r["source_timestamp"]) <= milliseconds(r["retrieved_at"]) <= cutoff,
                    "proof timestamp mismatch")
            require(r["freshness"] in ("current", "stale") and r["provenance_validated"] is True
                    and r["receipt_integrity_validated"] is True, "invalid proof validation")
            expected_unit = "fraction_per_interval" if r["metric"] == "funding_rate" else (
                "contracts" if r["provider"] == "okx" else "base_asset")
            require(r["unit"] == expected_unit, "proof unit mismatch")
            interval = r["funding_interval_seconds"]
            require(type(interval) is int and 3600 <= interval <= 86400 if r["metric"] == "funding_rate"
                    else interval is None, "invalid proof interval")
        else:
            require(r["status"] == "unavailable" and r["freshness"] == "unavailable"
                    and r["provenance_validated"] is False and r["receipt_integrity_validated"] is False
                    and all(r[k] is None for k in ("http_status", "api_status", "source_timestamp", "retrieved_at", "unit", "funding_interval_seconds")),
                    "unavailable proof mismatch")
    require(len(seen) == 4 and len(providers) == 1, "duplicate/mixed proof scope")
    a = p["archive"]
    require(set(a) == {"before_entry_hashes", "after_entry_hashes", "prior_entries_preserved", "distinct_fact_count", "fact_ids"}, "unsafe archive proof")
    for name, prefix in (("before_entry_hashes", "sha256:"), ("after_entry_hashes", "sha256:"), ("fact_ids", "evidence:")):
        require(isinstance(a[name], list) and a[name] == sorted(set(a[name])) and
                all(isinstance(v, str) and re.fullmatch(prefix + r"[0-9a-f]{64}", v) for v in a[name]), "invalid archive identity")
    require(a["prior_entries_preserved"] is True and set(a["before_entry_hashes"]) <= set(a["after_entry_hashes"]), "archive history lost")
    require(type(a["distinct_fact_count"]) is int and a["distinct_fact_count"] == len(a["fact_ids"]), "fact count mismatch")
    return True
