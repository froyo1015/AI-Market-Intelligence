"""Read-only receipt validation. Does not fetch, normalize or publish data."""

import hashlib
import json
import re
from dataclasses import fields
from datetime import datetime
from decimal import Decimal

from .production_schema import (ProductionObservation, InstrumentRevision,
                                ShadowObservationOutput, ProductionValidationResult)
from .validator import ContractError, require, shape, text, integer, decimal, fraction, digest

EPOCH = datetime(1970, 1, 1)
METRICS = {"funding_rate", "open_interest", "liquidation_quantity",
           "long_short_ratio", "positioning_change"}


def milliseconds(value):
    require(isinstance(value, str) and re.fullmatch(
        r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z", value), "timestamp precision")
    delta = datetime.strptime(value, "%Y-%m-%dT%H:%M:%S.%fZ") - EPOCH
    return delta.days * 86400000 + delta.seconds * 1000 + delta.microseconds // 1000


def content_hash(value):
    return digest({k: v for k, v in value.items() if k != "content_hash"})


def pointer(document, path):
    require(isinstance(path, str) and (path == "" or path.startswith("/")), "invalid pointer")
    if path == "":
        return document
    for token in path[1:].split("/"):
        require(not re.search(r"~(?![01])", token), "invalid pointer escape")
        token = token.replace("~1", "/").replace("~0", "~")
        if isinstance(document, list):
            require(bool(re.fullmatch(r"0|[1-9]\d*", token)), "invalid array pointer")
            document = document[int(token)]
        else:
            require(isinstance(document, dict), "unresolvable pointer")
            document = document[token]
    return document


def unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, "duplicate raw JSON key")
        result[key] = value
    return result


def reject_constant(value):
    raise ContractError("nonfinite raw JSON")


def index(items, model, key, prefix):
    require(isinstance(items, list), "invalid registry")
    result = {}
    for item in items:
        shape(item, [f.name for f in fields(model)])
        require(isinstance(item[key], str) and item[key].startswith(prefix) and
                "@" not in item[key], "invalid identity")
        integer(item["version"])
        ref = item[key] + "@" + str(item["version"])
        require(ref not in result, "duplicate revision")
        require(item["content_hash"] == content_hash(item), "content hash mismatch")
        result[ref] = item
    return result


def validate_output(output, raw_bytes, previous=None):
    """raw_bytes maps receipt paths to captured bytes; previous is optional history.

    This checks the supplied evidence, not the authenticity of its acquisition.
    """
    errors = []
    availability = "unavailable"
    try:
        availability = _validate(output, raw_bytes)
        if previous is not None:
            _history(output, previous)
    except (ContractError, ValueError, TypeError, KeyError, IndexError, OverflowError,
            RecursionError) as exc:
        errors.append(str(exc) if isinstance(exc, ContractError) else "malformed output")
    try:
        hashed = digest(output)
    except (ValueError, TypeError, RecursionError):
        hashed = None
    mode = output.get("replay_mode") if isinstance(output, dict) else None
    return ProductionValidationResult(errors, "unavailable" if errors else availability,
                                      "pass" if not errors and mode == "archived_point_in_time"
                                      else "indeterminate", hashed)


def _history(current, previous):
    require(isinstance(previous, dict), "invalid history")
    for collection, model, key, prefix in (
        ("instruments", InstrumentRevision, "instrument_id", "instrument:"),
        ("observations", ProductionObservation, "observation_id", "derivatives:observation:"),
    ):
        old = index(previous[collection], model, key, prefix)
        new = index(current[collection], model, key, prefix)
        for ref in old.keys() & new.keys():
            require(old[ref] == new[ref], "immutable revision changed")
    # Receipt identities are immutable too: prevent retroactive capture-time edits.
    for old in previous["receipts"]:
        for new in current["receipts"]:
            if old["receipt_id"] == new["receipt_id"]:
                require(old == new, "immutable receipt changed")


def _validate(a, raw):
    shape(a, [f.name for f in fields(ShadowObservationOutput)])
    require(a["schema_contract"] == "derivatives_shadow_output_v1" and a["synthetic"] is False,
            "non-synthetic shadow contract required")
    require(isinstance(a["run_id"], str) and re.fullmatch(r"[A-Za-z0-9_-]+", a["run_id"]), "unsafe run ID")
    request, cutoff = milliseconds(a["requested_cutoff"]), milliseconds(a["evaluation_cutoff"])
    require(request <= cutoff, "cutoff order")
    require(a["replay_mode"] in ("archived_point_in_time", "transformation_only"), "invalid replay mode")
    sources = {}
    require(isinstance(a["sources"], list), "invalid sources")
    for s in a["sources"]:
        shape(s, ("source_id", "publisher", "venue_id", "data_reliability"))
        for k in ("source_id", "publisher", "venue_id"):
            text(s[k])
        require(s["source_id"].startswith("source:") and s["venue_id"].startswith("venue:")
                and s["source_id"] not in sources, "invalid source identity")
        fraction(s["data_reliability"])
        sources[s["source_id"]] = s
    require(isinstance(raw, dict) and isinstance(a["receipts"], list), "invalid receipts")
    receipts, documents, paths = {}, {}, set()
    for r in a["receipts"]:
        shape(r, ("receipt_id", "source_id", "captured_at", "path", "sha256"))
        text(r["receipt_id"])
        require(r["receipt_id"].startswith("receipt:") and r["receipt_id"] not in receipts,
                "duplicate receipt")
        require(r["source_id"] in sources, "unknown source")
        milliseconds(r["captured_at"])
        path = r["path"]
        require(isinstance(path, str) and path.startswith("outputs/shadow/derivatives/" + a["run_id"] + "/")
                and all(re.fullmatch(r"[A-Za-z0-9_.-]+", p) and p not in (".", "..")
                        for p in path.split("/")), "unsafe shadow path")
        require(path not in paths and isinstance(raw.get(path), bytes), "missing/duplicate receipt bytes")
        paths.add(path)
        require(r["sha256"] == "sha256:" + hashlib.sha256(raw[path]).hexdigest(), "raw hash mismatch")
        documents[r["receipt_id"]] = json.loads(raw[path].decode("utf-8"), object_pairs_hook=unique_pairs,
                                                parse_constant=reject_constant)
        receipts[r["receipt_id"]] = r
    instruments = index(a["instruments"], InstrumentRevision, "instrument_id", "instrument:")
    observations = index(a["observations"], ProductionObservation, "observation_id", "derivatives:observation:")
    for i in instruments.values():
        require(i["metadata_receipt_ref"] in receipts, "missing metadata receipt")
        d = i["definition"]
        shape(d, ("venue_id", "native_symbol", "instrument_type", "base_asset_id", "quote_asset_id",
                  "settlement_asset_id", "underlying_asset_id", "oi_unit", "counting_basis",
                  "funding_interval_seconds", "funding_rate_kind", "funding_sign_convention",
                  "effective_from", "effective_to"))
        require(pointer(documents[i["metadata_receipt_ref"]], i["definition_pointer"]) == d,
                "metadata receipt mismatch")
        source = sources[receipts[i["metadata_receipt_ref"]]["source_id"]]
        require(d["venue_id"] == source["venue_id"], "metadata venue mismatch")
        text(d["native_symbol"])
        for k in ("base_asset_id", "quote_asset_id", "settlement_asset_id", "underlying_asset_id"):
            require(isinstance(d[k], str) and d[k].startswith("asset:"), "invalid asset reference")
        require(d["instrument_type"] in ("perpetual", "future"), "unsupported instrument")
        require(d["oi_unit"] in ("base_asset", "quote_asset", "contracts") and
                d["counting_basis"] in ("single_side", "both_sides"), "invalid OI definition")
        if d["funding_interval_seconds"] is not None:
            integer(d["funding_interval_seconds"])
        require(d["funding_rate_kind"] == "settled" and
                d["funding_sign_convention"] == "positive_long_pays_short", "unsupported funding semantics")
        start = milliseconds(d["effective_from"])
        require(d["effective_to"] is None or start < milliseconds(d["effective_to"]), "invalid effective range")
    for o in observations.values():
        require(o["schema_contract"] == "derivatives_production_observation_v1" and o["synthetic"] is False,
                "synthetic/unknown observation")
        require(o["instrument_ref"] in instruments and o["receipt_ref"] in receipts, "unresolved observation reference")
        i = instruments[o["instrument_ref"]]
        d = i["definition"]
        receipt, metadata = receipts[o["receipt_ref"]], receipts[i["metadata_receipt_ref"]]
        require(receipt["source_id"] == metadata["source_id"], "source mismatch")
        shape(o["pointers"], ("value", "timestamp", "symbol", "metric"))
        doc = documents[o["receipt_ref"]]
        require(pointer(doc, o["pointers"]["metric"]) == o["metric"], "metric receipt mismatch")
        require(pointer(doc, o["pointers"]["symbol"]) == d["native_symbol"], "instrument symbol mismatch")
        require(pointer(doc, o["pointers"]["value"]) == o["value"], "ungrounded value")
        value = decimal(o["value"])
        native = pointer(doc, o["pointers"]["timestamp"])
        require(type(native) is int and type(o["native_timestamp"]) is int and
                native == o["native_timestamp"] and o["native_time_unit"] in ("s", "ms"), "invalid native timestamp")
        observed = native * (1000 if o["native_time_unit"] == "s" else 1)
        require(milliseconds(o["source_timestamp"]) == observed, "timestamp precision loss")
        require(observed <= request, "future observation")
        require(milliseconds(d["effective_from"]) <= observed and
                (d["effective_to"] is None or observed < milliseconds(d["effective_to"])), "wrong instrument revision")
        retrieval, generated = milliseconds(o["retrieved_at"]), milliseconds(o["generated_at"])
        known = max(milliseconds(receipt["captured_at"]), milliseconds(metadata["captured_at"]))
        require(retrieval == milliseconds(receipt["captured_at"]) and observed <= retrieval and
                known <= generated and retrieval <= generated and milliseconds(o["known_at"]) == known,
                "incorrect knowledge/retrieval time")
        if a["replay_mode"] == "archived_point_in_time":
            require(known <= cutoff and generated <= cutoff, "PIT lookahead")
        metric = o["metric"]
        if metric == "funding_rate":
            require(d["instrument_type"] == "perpetual" and d["funding_interval_seconds"] is not None and
                    o["unit"] == "fraction_per_interval", "invalid funding definition")
            ttl = d["funding_interval_seconds"] + 1800
        else:
            require(metric == "open_interest" and value >= 0 and o["unit"] == d["oi_unit"], "invalid metric/unit")
            ttl = 7200
        age = Decimal(cutoff - observed) / 1000
        f = o["freshness"]
        shape(f, ("age_seconds", "freshness_status", "policy_id"))
        status = "current" if age <= ttl else "stale"
        require(decimal(f["age_seconds"]) == age and f["freshness_status"] == status and
                f["policy_id"] == "production-observation-freshness-v1", "freshness mismatch")
        q = o["evidence_quality"]
        shape(q, ("policy_id", "data_reliability", "timeliness", "temporal_coverage", "definition_consistency", "score"))
        reliability = sources[receipt["source_id"]]["data_reliability"]
        for k in ("data_reliability", "timeliness", "temporal_coverage", "definition_consistency", "score"):
            fraction(q[k])
        require(q["policy_id"] == "production-observation-quality-v1" and
                q["data_reliability"] == reliability and q["timeliness"] == int(status == "current") and
                q["temporal_coverage"] == 1 and q["definition_consistency"] == 1 and
                q["score"] == (None if reliability is None else min(reliability, int(status == "current"))),
                "quality mismatch")
    require(isinstance(a["coverage"], list), "invalid coverage")
    seen, available = set(), 0
    for c in a["coverage"]:
        shape(c, ("instrument_ref", "metric", "status", "reason"))
        key = (c["instrument_ref"], c["metric"])
        require(key not in seen and key[0] in instruments and key[1] in METRICS, "invalid coverage identity")
        seen.add(key)
        found = any(o["instrument_ref"] == key[0] and o["metric"] == key[1] for o in observations.values())
        require(c["status"] == ("available" if found else "unavailable"), "coverage mismatch")
        require(c["reason"] is None if found else c["reason"] in
                ("not_collected", "source_unavailable", "invalid_response", "insufficient_history"), "invalid missing reason")
        available += int(found)
    require(seen == {(ref, metric) for ref in instruments for metric in METRICS}, "incomplete coverage")
    return "unavailable" if not available else ("available" if available == len(seen) else "partial")
