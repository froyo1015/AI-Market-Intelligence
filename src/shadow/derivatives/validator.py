"""Closed, deterministic validation for synthetic V2 shadow artifacts."""

import copy
import hashlib
import json
import re
from dataclasses import fields
from datetime import datetime
from decimal import Decimal, InvalidOperation

from .schema import (Asset, Venue, Instrument, Source, DerivativesObservationV2,
                     DerivativesEvidenceV2, ValidationResult)


class ContractError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise ContractError(message)


def shape(value, names):
    require(isinstance(value, dict) and set(value) == set(names), "invalid fields")


def text(value):
    require(isinstance(value, str) and bool(value.strip()), "invalid text")


def integer(value):
    require(type(value) is int and value > 0, "invalid positive integer")


def timestamp(value):
    require(isinstance(value, str) and re.fullmatch(
        r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", value), "invalid UTC timestamp")
    return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")


def decimal(value):
    require(isinstance(value, str) and re.fullmatch(
        r"-?(?:0|[1-9]\d*)(?:\.\d*[1-9])?", value) and value != "-0",
        "invalid canonical decimal")
    result = Decimal(value)
    require(result.is_finite(), "nonfinite decimal")
    return result


def fraction(value):
    require(value is None or (type(value) in (int, float) and 0 <= value <= 1),
            "invalid quality fraction")


def refs(value, registry):
    require(isinstance(value, list) and all(isinstance(x, str) for x in value),
            "invalid references")
    require(len(set(value)) == len(value), "duplicate reference")
    require(all(x in registry for x in value), "unresolved reference")


def digest(value):
    return "sha256:" + hashlib.sha256(json.dumps(
        value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def record_hash(record):
    value = copy.deepcopy(record)
    value.pop("content_hash", None)
    for name in ("source_refs", "observation_refs", "related_assets"):
        value[name] = sorted(value[name])
    return digest(value)


def registry(items, model, id_key, prefix, versioned=True):
    require(isinstance(items, list), "registry must be list")
    result = {}
    for item in items:
        shape(item, [f.name for f in fields(model)])
        key = item[id_key]
        require(isinstance(key, str) and key.startswith(prefix) and "@" not in key,
                "invalid identity")
        if versioned:
            vkey = "record_version" if id_key == "record_id" else "version"
            integer(item[vkey])
            key += "@" + str(item[vkey])
        require(key not in result, "duplicate identity/revision")
        result[key] = item
    return result


def validate_artifact(artifact):
    """Never fetches, writes, or invokes consumers. Malformed JSON values fail closed."""
    errors = []
    try:
        _validate(artifact)
    except (ContractError, TypeError, ValueError, KeyError, OverflowError,
            InvalidOperation, RecursionError) as exc:
        errors.append(str(exc) if isinstance(exc, ContractError) else "malformed artifact")
    try:
        target_hash = digest(artifact)
    except (TypeError, ValueError, RecursionError):
        target_hash = None
    context = artifact if isinstance(artifact, dict) else {}
    mode = context.get("replay_mode")
    known_at = None
    if not errors:
        known_times = [r["known_at"] for r in context["observations"] + context["evidence"]]
        known_at = max(known_times) if known_times else None
    audit = {
        "schema_contract": "evidence_validation_event_v1",
        "validation_event_id": digest({"target": target_hash, "validator": "shadow-v2"}),
        "target_content_hash": target_hash,
        "target_ref": "artifact:shadow-derivatives@" + target_hash if target_hash else None,
        "run_id": context.get("run_id"),
        "input_artifact_refs": [],  # raw fixtures are embedded in the target artifact
        "validator_version": "shadow-v2",
        "policy_versions": ["derivatives-quality-v1", "derivatives-freshness-v1"],
        "evaluated_at": context.get("cutoff"),
        "known_at": known_at,
        "replay_cutoff": context.get("cutoff"),
        "replay_mode": mode,
        "result": "fail" if errors else "pass",
        "historical_availability": "indeterminate" if mode == "transformation_only"
        else ("fail" if errors else "pass"),
        "errors": list(errors),
        "checks": [
            {"rule_id": "shadow-contract-v2", "result": "fail" if errors else "pass",
             "reason_code": "invalid_contract" if errors else None},
            {"rule_id": "known-by-cutoff-v1", "result": "indeterminate" if errors or
             mode == "transformation_only" else "pass",
             "reason_code": "availability_not_established" if errors or
             mode == "transformation_only" else None},
        ],
        "supersedes_validation_event_ref": None,
    }
    return ValidationResult(errors, audit)


def _validate(a):
    shape(a, ("schema_contract", "synthetic", "run_id", "cutoff", "replay_mode", "assets",
              "venues", "instruments", "sources", "observations", "evidence", "coverage"))
    require(a["schema_contract"] == "derivatives_fixture_v2" and a["synthetic"] is True,
            "shadow synthetic contract required")
    cutoff = timestamp(a["cutoff"])
    text(a["run_id"])
    require(a["replay_mode"] in ("archived_point_in_time", "transformation_only"),
            "invalid replay mode")
    assets = registry(a["assets"], Asset, "asset_id", "asset:", False)
    venues = registry(a["venues"], Venue, "venue_id", "venue:", False)
    instruments = registry(a["instruments"], Instrument, "instrument_id", "instrument:")
    sources = registry(a["sources"], Source, "source_id", "source:")
    observations = registry(a["observations"], DerivativesObservationV2,
                            "record_id", "derivatives:observation:")
    evidence = registry(a["evidence"], DerivativesEvidenceV2,
                        "record_id", "derivatives:evidence:")
    for asset in assets.values():
        require(asset["asset_class"] in ("cryptoasset", "fiat", "equity", "commodity",
                                        "tokenized_security"), "invalid asset class")
        text(asset["symbol"])
        require(isinstance(asset["identifiers"], dict), "invalid identifiers")
        for k, v in asset["identifiers"].items():
            text(k)
            text(v)
    for venue in venues.values():
        text(venue["name"])
    for s in sources.values():
        require(s["venue_ref"] in venues, "unknown source venue")
        for name in ("publisher", "definition_version", "raw_locator"):
            text(s[name])
        require(s["raw_locator"].startswith("/"), "invalid raw locator")
        timestamp(s["retrieved_at"])
        fraction(s["data_reliability"])
        require(isinstance(s["raw_payload"], dict) and s["raw_hash"] == digest(s["raw_payload"]),
                "raw hash mismatch")
    for i in instruments.values():
        require(i["venue_ref"] in venues, "unknown venue")
        for key in ("base_asset_ref", "quote_asset_ref", "settlement_asset_ref"):
            require(i[key] in assets, "unknown asset")
        require(i["underlying_asset_ref"] is None or i["underlying_asset_ref"] in assets,
                "unknown underlying")
        kind = i["instrument_type"]
        require(kind in ("spot", "perpetual", "future", "option", "tokenized_share"),
                "invalid instrument type")
        if kind in ("perpetual", "future", "option"):
            shape(i["contract"], ("size", "unit", "expiry"))
            require(decimal(i["contract"]["size"]) > 0, "invalid contract size")
            require(i["contract"]["unit"] in ("base_asset", "quote_asset", "contracts"),
                    "invalid contract unit")
            require(i["underlying_asset_ref"] is not None, "missing underlying")
            if kind == "perpetual":
                require(i["contract"]["expiry"] is None, "perpetual has expiry")
            else:
                timestamp(i["contract"]["expiry"])
        else:
            require(i["contract"] is None, "unexpected contract")
        if kind == "tokenized_share":
            t = i["token"]
            shape(t, ("chain", "network", "address", "issuer", "decimals",
                      "redemption_ratio", "documentation_refs"))
            for key in ("chain", "network", "address", "issuer"):
                text(t[key])
            require(type(t["decimals"]) is int and 0 <= t["decimals"] <= 255,
                    "invalid token decimals")
            refs(t["documentation_refs"], sources)
            if t["redemption_ratio"] is not None:
                require(decimal(t["redemption_ratio"]) > 0 and t["documentation_refs"],
                        "unverified redemption ratio")
        else:
            require(i["token"] is None, "unexpected token extension")

    visiting, done = set(), set()

    def visit(ref):
        require(ref not in visiting, "cyclic observation lineage")
        if ref in done:
            return
        visiting.add(ref)
        r = observations[ref]
        refs(r["observation_refs"], observations)
        for dep in r["observation_refs"]:
            visit(dep)
        check_record(r, False, a, cutoff, assets, instruments, sources, observations)
        visiting.remove(ref)
        done.add(ref)

    for ref in observations:
        visit(ref)
    for r in evidence.values():
        check_record(r, True, a, cutoff, assets, instruments, sources, observations)
    require(isinstance(a["coverage"], list), "invalid coverage")
    seen = set()
    supported = {"funding_rate", "open_interest", "liquidation_quantity",
                 "long_short_ratio", "positioning_change"}
    for cell in a["coverage"]:
        shape(cell, ("instrument_ref", "metric", "status", "missing_reason"))
        key = (cell["instrument_ref"], cell["metric"])
        require(key[0] in instruments and key[1] in supported and key not in seen,
                "invalid/duplicate coverage cell")
        seen.add(key)
        found = any((r["instrument_ref"], r["payload"]["metric"]) == key
                    for r in observations.values())
        require(cell["status"] == ("available" if found else "unavailable"),
                "coverage contradicts records")
        if found:
            require(cell["missing_reason"] is None, "available metric has missing reason")
        else:
            require(cell["missing_reason"] in ("not_collected", "unsupported", "source_unavailable",
                    "invalid_response", "incomplete_window", "insufficient_history",
                    "unknown_contract_definition", "zero_denominator"), "invalid missing reason")
    required = {(r["instrument_ref"], metric) for r in observations.values() for metric in supported}
    require(required <= seen, "missing metric coverage cells")


def check_record(r, is_evidence, a, cutoff, assets, instruments, sources, observations):
    require(r["schema_contract"] == ("derivatives_evidence_v2" if is_evidence else
                                     "derivatives_observation_v2"), "invalid record schema")
    require(r["content_hash"] == record_hash(r), "record hash mismatch")
    require(r["instrument_ref"] in instruments, "unknown instrument")
    instrument = instruments[r["instrument_ref"]]
    require(instrument["instrument_type"] in ("perpetual", "future", "option"),
            "derivative measurement needs derivative instrument")
    refs(r["related_assets"], assets)
    require(set(r["related_assets"]) == {instrument["base_asset_ref"]}, "asset mapping mismatch")
    refs(r["source_refs"], sources)
    require(bool(r["source_refs"]), "source required")
    require(all(sources[s]["venue_ref"] == instrument["venue_ref"] for s in r["source_refs"]),
            "source venue mismatch")
    refs(r["observation_refs"], observations)
    deps = [observations[d] for d in r["observation_refs"]]
    require(all(d["instrument_ref"] == r["instrument_ref"] for d in deps), "cross-instrument dependency")
    require(set().union(*(set(d["source_refs"]) for d in deps)) <= set(r["source_refs"]),
            "lost dependency provenance")
    times = r["timestamps"]
    shape(times, ("observed_at", "published_at", "retrieved_at", "generated_at"))
    observed = timestamp(times["observed_at"]) if times["observed_at"] is not None else None
    retrieved, generated = timestamp(times["retrieved_at"]), timestamp(times["generated_at"])
    require(retrieved <= generated, "retrieval after generation")
    require(observed is None or observed <= min(retrieved, cutoff), "future observation")
    if times["published_at"] is not None:
        require(timestamp(times["published_at"]) <= retrieved, "publication after retrieval")
    known = max([timestamp(sources[s]["retrieved_at"]) for s in r["source_refs"]] +
                [timestamp(d["known_at"]) for d in deps])
    require(timestamp(r["known_at"]) == known and known <= retrieved, "incorrect known_at")
    if a["replay_mode"] == "archived_point_in_time":
        require(known <= cutoff, "lookahead evidence")

    p = r["payload"]
    require(isinstance(p, dict), "invalid payload")
    metric = p.get("metric")
    extra = {
        "funding_rate": ("rate_kind", "interval_seconds", "settlement_at", "sign_convention"),
        "open_interest": ("counting_basis",),
        "liquidation_quantity": ("side", "window_start", "window_end", "coverage_fraction"),
        "long_short_ratio": ("basis", "population", "period_seconds"),
        "positioning_change": ("formula_id",),
    }
    require(metric in extra, "unsupported metric")
    shape(p, ("metric", "value", "unit") + extra[metric])
    value = decimal(p["value"])
    ttl = 7200
    if metric == "funding_rate":
        require(p["unit"] == "fraction_per_interval" and p["rate_kind"] in ("settled", "indicated")
                and p["sign_convention"] == "positive_long_pays_short", "invalid funding definition")
        integer(p["interval_seconds"])
        settlement = timestamp(p["settlement_at"])
        require(observed is not None and (settlement == observed if p["rate_kind"] == "settled"
                                         else settlement >= observed), "invalid settlement time")
        ttl = p["interval_seconds"] + 1800
    elif metric in ("open_interest", "liquidation_quantity"):
        require(p["unit"] in ("base_asset", "quote_asset", "contracts") and value >= 0,
                "invalid quantity/unit")
        if metric == "open_interest":
            require(p["counting_basis"] in ("single_side", "both_sides"), "invalid counting basis")
        else:
            start, end = timestamp(p["window_start"]), timestamp(p["window_end"])
            fraction(p["coverage_fraction"])
            require(start < end and end == observed and p["side"] in ("long", "short"),
                    "invalid liquidation window/side")
            require(value != 0 or p["coverage_fraction"] == 1, "unproven zero liquidation")
    elif metric == "long_short_ratio":
        require(p["unit"] == "ratio" and value >= 0 and p["basis"] in ("account_count", "notional")
                and p["population"] in ("all_accounts", "top_accounts", "positions"), "invalid ratio")
        integer(p["period_seconds"])
    else:
        require(p["unit"] == "percent" and p["formula_id"] == "relative_change_v1", "invalid formula")
        if not is_evidence:
            require(len(deps) == 2, "positioning needs two observations")
            ordered = sorted(deps, key=lambda d: timestamp(d["timestamps"]["observed_at"]))
            left, right = [d["payload"] for d in ordered]
            require(left["metric"] == right["metric"] == "open_interest" and
                    left["unit"] == right["unit"] and left["counting_basis"] == right["counting_basis"],
                    "incompatible positioning inputs")
            require(ordered[0]["timestamps"]["observed_at"] < ordered[1]["timestamps"]["observed_at"]
                    and times["observed_at"] == ordered[1]["timestamps"]["observed_at"], "invalid positioning window")
            baseline = decimal(left["value"])
            require(baseline > 0 and value == (decimal(right["value"])/baseline - 1)*100,
                    "positioning arithmetic mismatch")
    if is_evidence:
        require(r["claim_type"] == "measurement_report" and deps, "unsupported claim")
        require(all(d["payload"] == p and d["timestamps"]["observed_at"] == times["observed_at"]
                    for d in deps), "unsupported factual claim")
        require(set(r["source_refs"]) == set().union(*(set(d["source_refs"]) for d in deps)),
                "unsupported source attribution")
    elif metric != "positioning_change":
        require(not deps, "unexpected measurement dependencies")
        measurement = {"instrument_ref": r["instrument_ref"], "payload": p,
                       "observed_at": times["observed_at"]}
        for source_ref in r["source_refs"]:
            source = sources[source_ref]
            require(source["raw_locator"] == "/measurements" and
                    isinstance(source["raw_payload"].get("measurements"), list) and
                    measurement in source["raw_payload"]["measurements"],
                    "measurement not grounded in raw fixture")

    f = r["freshness"]
    shape(f, ("source_timestamp", "retrieved_at", "generated_at", "age_seconds", "freshness_status", "policy_id"))
    age = (cutoff - observed).total_seconds() if observed is not None else None
    status = "unknown" if age is None else ("current" if age <= ttl else "stale")
    require(f["source_timestamp"] == times["observed_at"] and f["retrieved_at"] == times["retrieved_at"]
            and f["generated_at"] == times["generated_at"] and f["age_seconds"] == age
            and f["freshness_status"] == status and f["policy_id"] == "derivatives-freshness-v1",
            "freshness mismatch")
    q = r["evidence_quality"]
    shape(q, ("quality_policy_version", "score", "components"))
    require(q["quality_policy_version"] == "derivatives-quality-v1", "unknown quality policy")
    c = q["components"]
    shape(c, ("data_reliability", "timeliness", "temporal_coverage", "definition_consistency"))
    for item in list(c.values()) + [q["score"]]:
        fraction(item)
    reliability = [sources[s]["data_reliability"] for s in r["source_refs"]]
    require(c["data_reliability"] == (None if None in reliability else min(reliability)), "reliability mismatch")
    require(c["timeliness"] == (None if status == "unknown" else int(status == "current"))
            and c["definition_consistency"] == 1, "quality semantics mismatch")
    if metric == "liquidation_quantity":
        require(c["temporal_coverage"] == p["coverage_fraction"], "coverage quality mismatch")
    expected = None if None in c.values() else min(c.values())
    require(q["score"] == expected, "quality score mismatch")
    for dep in deps:
        score = dep["evidence_quality"]["score"]
        require(q["score"] is None or (score is not None and q["score"] <= score), "quality exceeds dependency")
