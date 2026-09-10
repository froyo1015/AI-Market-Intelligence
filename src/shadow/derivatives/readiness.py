"""Review-only derivatives readiness. Never enables production."""

import argparse
import json
from datetime import datetime, timedelta
from pathlib import Path

from src.intelligence.evidence_boundary import write_context
from .context_evaluation import evaluate, SLOTS
from .production_validator import milliseconds, unique_pairs, reject_constant
from .validator import digest, require

POLICY = "derivatives-shadow-readiness-v1"
CURRENT_KEYS = set("id type related_assets instrument_id venue_id source_records observations events evidence_records timestamps verification_level validation_status data_quality freshness current_eligible provenance".split())
FORBIDDEN = set("bullish bearish sentiment prediction trading_signal recommendation ranking market_impact api_key authorization headers raw_response body_base64 secret access_token prompt".split())


def _safe(value):
    if isinstance(value, dict):
        return not any(str(k).lower() in FORBIDDEN for k in value) and all(_safe(v) for v in value.values())
    if isinstance(value, list):
        return all(_safe(v) for v in value)
    return True


def assess(history, as_of):
    cutoff = milliseconds(as_of)
    require(isinstance(history, list), "invalid history root")
    day = datetime.strptime(as_of[:10], "%Y-%m-%d")
    dates = {(day - timedelta(days=n)).strftime("%Y-%m-%d") for n in range(7)}
    checks = dict.fromkeys(("input_integrity", "availability", "freshness", "provenance", "coverage", "safety"), True)
    rows, seen, bundles, times, observed = [], set(), set(), set(), set()
    duplicates = outside = 0
    latest = None
    for pair in history:
        try:
            require(isinstance(pair, dict) and set(pair) == {"bundle", "context"}, "invalid sample")
            h = digest(pair)
            if h in seen:
                duplicates += 1
                continue
            seen.add(h)
            b, c = pair["bundle"], pair["context"]
            section = c["derivatives_evidence"]
            stamp = section["evaluated_at"]
            t = milliseconds(stamp)
            require(t <= cutoff, "future sample")
            if stamp[:10] not in dates:
                outside += 1
                continue
            bh = digest(b) if b is not None else None
            require(t not in times, "conflicting sample cutoff")
            require(bh is None or bh not in bundles, "reused bundle")
            times.add(t)
            if bh is not None:
                bundles.add(bh)
            observed.add(stamp[:10])
            latest = max(t, latest) if latest is not None else t
            r = evaluate(b, c)
            valid = r["validation_status"] == "validated"
            m = r["metrics"] if valid else None
            current = section["current_facts"]
            covered = {(f["instrument_id"], o["metric"]) for f in current for o in f["observations"]}
            sample = {
                "input_integrity": valid,
                "availability": bool(m and m["data_availability"]["value"] == 1),
                "freshness": bool(m and m["freshness_success_rate"]["value"] == 1),
                "provenance": bool(m and m["provenance_completeness"]["value"] == 1),
                "coverage": valid and covered == SLOTS,
                "safety": section["scope"] == "read_only_facts" and _safe(b) and _safe(section)
                          and all(set(f) == CURRENT_KEYS and not f["events"]
                                  and f["type"] == "derivatives_observation" for f in current),
            }
            for k, passed in sample.items():
                checks[k] &= passed
            rows.append({"sample_hash": h, "evaluated_at": stamp, "input_hashes": r["input_hashes"],
                         "checks": sample})
        except (ValueError, TypeError, KeyError, IndexError, ArithmeticError):
            checks["input_integrity"] = False
            rows.append({"error": "invalid_history_sample"})
    history_ok = observed == dates and latest is not None and cutoff - latest <= 86400000
    status = "blocked" if not all(checks.values()) else "passing" if history_ok else "insufficient_history"
    checks["history"] = history_ok
    return {"schema_contract": "derivatives_readiness_v1", "policy_id": POLICY,
            "evaluated_at": as_of, "status": status, "production_enabled": False,
            "checks": checks, "history": {"required_dates": sorted(dates), "observed_dates": sorted(observed),
                "unique_sample_count": len(times), "duplicate_count": duplicates, "outside_window_count": outside,
                "latest_sample_age_seconds": (cutoff - latest) / 1000 if latest is not None else None},
            "samples": sorted(rows, key=lambda r: (r.get("evaluated_at", ""), r.get("sample_hash", "")))}


def validate_readiness(result, history, as_of):
    return result == assess(history, as_of)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--history", required=True)
    parser.add_argument("--as-of", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    history = json.loads(Path(args.history).read_text(), object_pairs_hook=unique_pairs, parse_constant=reject_constant)
    write_context(assess(history, args.as_of), args.output)


if __name__ == "__main__":
    main()
