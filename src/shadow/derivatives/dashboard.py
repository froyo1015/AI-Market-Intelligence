"""Explicit public projection of replay-validated existing archive only."""
import argparse
import json
from pathlib import Path

from src.intelligence.evidence_boundary import read, check_output_path
from src.pages.derivatives_schema import validate_public
from .archive import replay, readiness
from .production_validator import milliseconds
from .validator import require


def project(root, as_of):
    cutoff = milliseconds(as_of)
    rows = [{"asset": a, "metric": m, "value": None,
             "unit": "fraction" if m == "funding_rate" else "base_asset",
             "source_timestamp": None, "freshness_status": "unavailable", "ttl_seconds": 30600 if m == "funding_rate" else 7200,
             "evidence_quality": None, "provenance_status": "unavailable"}
            for a in ("BTC", "ETH") for m in ("funding_rate", "open_interest")]
    result = {"schema_contract": "derivatives_public_v1", "generated_at": as_of,
              "validation_status": "unavailable", "measurements": rows,
              "readiness": {"current_history_days": 0, "required_history_days": 7,
                            "production_enabled": False, "blocking_reasons": ["unavailable"]}}
    try:
        root = check_output_path(root)
        gate = readiness(root, as_of)
        result["readiness"].update(current_history_days=len(gate["history"]["observed_dates"]),
            blocking_reasons=sorted(k for k, ok in gate["checks"].items() if not ok))
        result["readiness"]["tracking"] = gate["tracking"]
        entries = []
        for path in sorted(root.glob("*/*.json")):
            check_output_path(path)
            e = read(path)
            replay(e)
            if milliseconds(e["request"]["archived_at"]) <= cutoff:
                entries.append(e)
        if not entries:
            return result
        latest = max(entries, key=lambda e: (e["request"]["cutoff"], e["request"]["archived_at"]))
        # Do not resurrect a prior successful run after an unavailable latest run.
        from .context_evaluation import evaluate
        require(evaluate(latest["bundle"], latest["context"])["validation_status"] == "validated", "invalid context")
        for row in rows:
            facts = [f for f in latest["bundle"]["evidence"] if f["instrument_id"] ==
                     "instrument:binance-usdm-" + row["asset"].lower() + "usdt" and f["metric"] == row["metric"]]
            if not facts:
                continue
            newest = max(f["source_timestamp"] for f in facts)
            selected = [f for f in facts if f["source_timestamp"] == newest]
            if len(selected) != 1 or selected[0]["conflict"]:
                continue
            f = selected[0]
            ttl = f["metric_definition"]["funding_interval_seconds"] + 1800 if row["metric"] == "funding_rate" else 7200
            current = 0 <= cutoff - milliseconds(newest) <= ttl * 1000
            scores = [s["observation"]["evidence_quality"]["score"] for s in f["source_records"]]
            row.update(value=f["value"], source_timestamp=newest, ttl_seconds=ttl,
                       freshness_status="current" if current else "stale", provenance_status="complete",
                       evidence_quality=None if None in scores else min(*scores, int(current)))
        result["validation_status"] = "validated" if any(r["value"] is not None for r in rows) else "unavailable"
        require(validate_public(result), "invalid projection")
    except (ValueError, KeyError, TypeError, AssertionError, OSError):
        for row in rows:
            row.update(value=None, source_timestamp=None, freshness_status="unavailable", evidence_quality=None, provenance_status="unavailable")
        result["validation_status"] = "unavailable"
        result["readiness"].update(current_history_days=0, blocking_reasons=["invalid_archive"])
        result["readiness"].pop("tracking", None)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", required=True)
    parser.add_argument("--as-of", required=True)
    parser.add_argument("--output", default="docs/derivatives-shadow.json")
    args = parser.parse_args()
    result = project(Path(args.archive), args.as_of)
    require(validate_public(result), "invalid public artifact")
    target = Path(args.output)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    main()
