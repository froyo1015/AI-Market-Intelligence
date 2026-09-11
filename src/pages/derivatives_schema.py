"""Closed public projection contract: raw shadow structures are never allowed."""
import math
import re
from datetime import datetime

BLOCKS = {"history", "availability", "freshness", "provenance", "coverage", "safety", "input_integrity", "invalid_archive", "unavailable"}


def validate_public(payload):
    if not __debug__:
        return False  # Never bypass the closed contract under python -O.
    try:
        assert set(payload) == {"schema_contract", "generated_at", "validation_status", "measurements", "readiness"}
        assert payload["schema_contract"] == "derivatives_public_v1"
        timestamp(payload["generated_at"])
        assert payload["validation_status"] in ("validated", "unavailable")
        assert len(payload["measurements"]) == 4
        slots = set()
        for m in payload["measurements"]:
            assert set(m) == {"asset", "metric", "value", "unit", "source_timestamp", "freshness_status", "ttl_seconds", "evidence_quality", "provenance_status"}
            assert m["asset"] in ("BTC", "ETH") and m["metric"] in ("funding_rate", "open_interest")
            slots.add((m["asset"], m["metric"]))
            assert m["unit"] == ("fraction" if m["metric"] == "funding_rate" else "base_asset")
            assert type(m["ttl_seconds"]) is int and 0 < m["ttl_seconds"] <= 90000
            assert m["freshness_status"] in ("current", "stale", "unavailable")
            assert m["provenance_status"] in ("complete", "unavailable")
            q = m["evidence_quality"]
            assert q is None or type(q) in (int, float) and math.isfinite(q) and 0 <= q <= 1
            if m["value"] is None:
                assert m["source_timestamp"] is None and m["freshness_status"] == "unavailable" and m["provenance_status"] == "unavailable" and q is None
            else:
                assert payload["validation_status"] == "validated" and m["provenance_status"] == "complete"
                assert isinstance(m["value"], str) and len(m["value"]) <= 80 and re.fullmatch(r"-?(?:0|[1-9]\d*)(?:\.\d+)?", m["value"])
                timestamp(m["source_timestamp"])
                assert m["freshness_status"] in ("current", "stale")
        assert len(slots) == 4
        r = payload["readiness"]
        base = {"current_history_days", "required_history_days", "production_enabled", "blocking_reasons"}
        assert set(r) in (base, base | {"tracking"})
        if "tracking" in r:
            t = r["tracking"]
            assert set(t) == {"collected_days", "missing_days", "sample_count", "freshness_pass_rate", "provenance_completeness", "validation_failures"}
            assert t["collected_days"] == r["current_history_days"] and type(t["collected_days"]) is int
            assert type(t["sample_count"]) is int and t["sample_count"] >= 0
            assert type(t["validation_failures"]) is int and 0 <= t["validation_failures"] <= t["sample_count"]
            assert isinstance(t["missing_days"], list) and len(set(t["missing_days"])) == len(t["missing_days"]) == 7 - t["collected_days"]
            for day in t["missing_days"]:
                assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", day)
                datetime.strptime(day, "%Y-%m-%d")
            for key in ("freshness_pass_rate", "provenance_completeness"):
                v = t[key]
                assert v is None if t["sample_count"] == 0 else type(v) in (int, float) and math.isfinite(v) and 0 <= v <= 1
        assert type(r["current_history_days"]) is int and 0 <= r["current_history_days"] <= 7
        assert type(r["required_history_days"]) is int and r["required_history_days"] == 7
        assert r["production_enabled"] is False
        assert isinstance(r["blocking_reasons"], list) and all(x in BLOCKS for x in r["blocking_reasons"])
        return True
    except (AssertionError, ValueError, TypeError, KeyError, OverflowError):
        return False


def timestamp(value):
    assert isinstance(value, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z", value)
    return datetime.strptime(value, "%Y-%m-%dT%H:%M:%S.%fZ")


if __name__ == "__main__":
    import argparse
    import json
    from pathlib import Path
    parser = argparse.ArgumentParser(description="Validate public shadow artifact before Pages publication")
    parser.add_argument("source")
    parser.add_argument("target")
    args = parser.parse_args()
    payload = json.loads(Path(args.source).read_text())
    if not validate_public(payload):
        raise SystemExit("Invalid public shadow projection")
    Path(args.target).write_text(json.dumps(payload, indent=2) + "\n")
