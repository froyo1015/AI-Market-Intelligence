"""Daily shadow collection only; no production writers or consumers."""

import argparse
import json
from pathlib import Path

from src.intelligence.evidence_boundary import read, write_context, check_output_path
from src.intelligence.validator import validate_daily_intelligence_artifact
from .archive import append, history, readiness, replay
from .binance_funding import BinanceFundingAdapter, PROVIDER, REFS, utc_now
from .binance_open_interest import BinanceOpenInterestAdapter
from .provider_security import ProviderRequest, EnvironmentSecretAccess
from .validator import require


def fact_index(root):
    records = {}
    for path in sorted(Path(root).glob("*/*.json")):
        check_output_path(path)
        entry = read(path)
        replay(entry)
        for fact in entry["bundle"]["evidence"]:
            item = records.setdefault(fact["evidence_id"], {"evidence_id": fact["evidence_id"],
                "observation_refs": set(), "archive_refs": set()})
            item["observation_refs"].update(fact["observation_refs"])
            item["archive_refs"].add(entry["entry_hash"])
    return {"schema_contract": "derivatives_observation_index_v1", "facts": [
        {"evidence_id": k, "observation_refs": sorted(records[k]["observation_refs"]),
         "archive_refs": sorted(records[k]["archive_refs"])} for k in sorted(records)]}


def run(root, output, daily, upstream, run_id, clock=utc_now, adapters=None):
    root, output = check_output_path(root), check_output_path(output)
    require(not output.exists(), "shadow run output already exists")
    validate_daily_intelligence_artifact(daily, *upstream)
    history(root, clock())  # verify checkpoint before collection
    adapters = adapters if adapters is not None else (
        BinanceFundingAdapter(run_id + "-funding"), BinanceOpenInterestAdapter(run_id + "-oi"))
    wrappers = []
    for adapter, metric in zip(adapters, ("funding_rate", "open_interest")):
        adapter.collect(ProviderRequest(PROVIDER, tuple(REFS.values()), (metric,)), EnvironmentSecretAccess(set()))
        wrappers.append(adapter.artifact)
    require(len(wrappers) == 2, "missing adapters")
    # Adapter validators admit only closed failure codes. Report those codes,
    # never provider bodies, headers, receipts or credentials, for live recovery.
    print("Shadow provider health: " + json.dumps([
        {"metric": metric, "status": artifact["status"],
         "symbols": artifact["symbol_status"], "failure_codes": artifact["failures"]}
        for metric, artifact in zip(("funding_rate", "open_interest"), wrappers)
    ], sort_keys=True))
    cutoff = clock()
    path = append(root, {"funding": [wrappers[0]], "oi": [wrappers[1]], "daily": daily,
                        "upstream": list(upstream), "cutoff": cutoff, "archived_at": clock()})
    result = readiness(root, clock())
    write_context(fact_index(root), output / "observation_index.json")
    write_context(result, output / "derivatives_readiness.json")
    from .dashboard import project
    from src.pages.derivatives_schema import validate_public
    public = project(root, result["evaluated_at"])
    require(validate_public(public), "invalid public projection")
    write_context(public, output / "derivatives-shadow.json")
    write_context({"schema_contract": "derivatives_shadow_run_v1", "production_enabled": False,
                   "archive_entry": read(path)["entry_hash"],
                   "provider_status": [a["status"] for a in wrappers],
                   "readiness_status": result["status"]}, output / "shadow_run.json")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    base = Path("src/output")
    daily = read(base / "daily_intelligence.json")
    upstream = [read(base / (n + ".json")) for n in ("evidence_bundle", "market_signals", "market_regime", "risk_monitor")]
    result = run(Path(args.archive), Path(args.output), daily, upstream, args.run_id)
    print("Shadow readiness: " + result["status"])


if __name__ == "__main__":
    main()
