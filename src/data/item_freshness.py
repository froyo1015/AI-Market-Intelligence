"""Reference-scoped freshness metadata; does not rank or interpret facts."""
from collections import defaultdict
from collections.abc import Mapping

VERSION = "reference_scoped_v1"
ID_FIELDS = ("observation_id", "event_id", "evidence_id", "signal_id", "risk_id", "item_id", "object_id", "id")
COLLECTIONS = ("records", "observations", "events", "evidence", "bundles", "signals", "dimensions", "risks", "items",
               "cross_asset_signals", "upcoming_events", "data_quality_risks", "observed_market_stress")


def walk(value):
    if isinstance(value, Mapping):
        yield value
        for key, child in value.items():
            if key != "freshness_items":
                yield from walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk(child)


def item_id(item):
    return next((str(item[k]) for k in ID_FIELDS if item.get(k)), str(item.get("symbol", item.get("dimension_id", ""))))


def targets(artifact):
    result = {}
    for field in COLLECTIONS:
        for item in artifact.get(field, []) if isinstance(artifact.get(field), list) else []:
            if isinstance(item, Mapping) and item_id(item):
                result[item_id(item)] = item
    if isinstance(artifact.get("market_regime"), Mapping):
        item = artifact["market_regime"]
        if item_id(item):
            result[item_id(item)] = item
    return result


def build_item_freshness(artifact, supporting=()):
    from src.data.freshness import enrich_artifact_freshness, _parse_timestamp, MAXIMUM_FUTURE_SKEW_SECONDS
    from src.models.freshness_schema import STALE_AFTER_SECONDS, DEFAULT_STALE_AFTER_SECONDS
    observations, events, sources, evidence, bundles = [defaultdict(list) for _ in range(5)]
    for root in (artifact, *supporting):
        for row in walk(root):
            if row.get("observation_id") and row.get("as_of"):
                observations[str(row["observation_id"])].append(row)
            if row.get("event_id") and (row.get("published_at") or row.get("retrieved_at")):
                events[str(row["event_id"])].append(row)
            if row.get("source_id") and row.get("retrieved_at"):
                sources[str(row["source_id"])].append(row)
            if row.get("evidence_id") and "observation_ids" in row:
                evidence[str(row["evidence_id"])].append(row)
            if row.get("id") and isinstance(row.get("provenance"), Mapping):
                bundles[str(row["id"])].append(row)

    records = {}
    threshold = STALE_AFTER_SECONDS.get(artifact.get("artifact_type"), DEFAULT_STALE_AFTER_SECONDS)
    for identifier, item in targets(artifact).items():
        refs = item.get("evidence_refs", item.get("provenance", item))
        obs_ids = set(refs.get("observation_ids", []))
        event_ids = set(refs.get("event_ids", []))
        source_ids = set(refs.get("source_ids", refs.get("supporting_source_ids", [])))
        if item.get("observation_id"):
            obs_ids.add(item["observation_id"])
        if item.get("event_id"):
            event_ids.add(item["event_id"])
        # Resolve broad references only when direct observation/event references
        # are absent; a catalog may contain unrelated bundles and sources.
        if not obs_ids and not event_ids:
            for eid in refs.get("evidence_ids", []):
                for row in evidence.get(eid, []):
                    obs_ids.update(row.get("observation_ids", []))
                    event_ids.update(row.get("event_ids", []))
            for bid in refs.get("evidence_bundle_ids", []):
                for row in bundles.get(bid, []):
                    obs_ids.update(row["provenance"].get("observation_ids", []))
                    event_ids.update(row["provenance"].get("event_ids", []))
        selected = [r for oid in sorted(obs_ids) for r in observations.get(oid, [])]
        event_rows = [r for eid in sorted(event_ids) for r in events.get(eid, [])]
        source_ids.update(r.get("source_id") for r in selected if r.get("source_id"))
        missing = any(not observations.get(oid) for oid in obs_ids) or any(not events.get(eid) for eid in event_ids)
        timestamps = [r["as_of"] for r in selected]
        timestamps += [r["published_at"] for r in event_rows if r.get("published_at")]
        # Direct adapter record: timestamp is observation time, not retrieval time.
        if item.get("symbol") and item.get("timestamp"):
            timestamps.append(item["timestamp"])
        receipts = [r["retrieved_at"] for sid in sorted(source_ids) for r in sources.get(sid, [])]
        receipts += [r["retrieved_at"] for r in event_rows if r.get("retrieved_at")]
        if item.get("retrieved_at"):
            receipts.append(item["retrieved_at"])
        if item.get("symbol") and artifact.get("retrieved_at"):
            receipts.append(artifact["retrieved_at"])
        missing = missing or any(not sources.get(sid) for sid in source_ids)
        parsed = [_parse_timestamp(value) for value in timestamps]
        assessment = _parse_timestamp(artifact["generated_at"])
        missing = missing or any(value is None or (value - assessment).total_seconds() > MAXIMUM_FUTURE_SKEW_SECONDS for value in parsed)
        failed = artifact.get("status") in {"failed", "invalid", "unavailable"} or item.get("status") in {"failed", "invalid", "unavailable"} or any(r.get("status") in {"failed", "invalid", "unavailable"} for r in selected)
        failed = failed or any(r.get("status") in {"failed", "invalid", "unavailable"} for sid in source_ids for r in sources.get(sid, []))
        leaf = {"artifact_type": "item_freshness", "generated_at": artifact["generated_at"],
                "observed_at": timestamps, "retrieved_at": max(receipts) if receipts else None}
        if missing or failed or (not timestamps and not (event_rows and receipts)):
            leaf["status"] = "unavailable"
        item_threshold = min(threshold, 86400) if any(r.get("scheduled_at") for r in event_rows) else threshold
        receipt_inputs = [{"retrieved_at": max(receipts)}] if receipts else []
        metadata = enrich_artifact_freshness(leaf, receipt_inputs, stale_after_seconds=item_threshold)
        if metadata["freshness_status"] == "current" and (item.get("status") == "stale" or any(r.get("status") == "stale" for r in selected)):
            # A provider's explicit stale flag is never overridden by a recent
            # clock value. Contradictory metadata is unavailable, not upgraded.
            leaf["status"] = "unavailable"
            metadata = enrich_artifact_freshness(leaf, receipt_inputs, stale_after_seconds=item_threshold)
        from src.data.freshness import FRESHNESS_FIELDS
        row = {k: metadata[k] for k in sorted(FRESHNESS_FIELDS | {"generated_at"})}
        row["observation_ids"] = sorted(obs_ids)
        row["event_ids"] = sorted(event_ids)
        row["source_ids"] = sorted(source_ids)
        records[identifier] = row
    return {"version": VERSION, "items": dict(sorted(records.items()))}


def validate_item_freshness(extension, generated_at):
    from src.data.freshness import FRESHNESS_FIELDS, validate_freshness_contract
    if not isinstance(extension, Mapping) or set(extension) != {"version", "items"} or extension["version"] != VERSION or not isinstance(extension["items"], Mapping):
        raise ValueError("invalid item freshness extension")
    allowed = (FRESHNESS_FIELDS - {"freshness_items"}) | {"generated_at", "observation_ids", "event_ids", "source_ids"}
    for identifier, item in extension["items"].items():
        if not isinstance(identifier, str) or not identifier or not isinstance(item, Mapping) or set(item) != allowed:
            raise ValueError("invalid item freshness fields")
        if item["generated_at"] != generated_at:
            raise ValueError("item freshness assessment timestamp mismatch")
        if type(item["stale_after_seconds"]) is not int or item["stale_after_seconds"] <= 0:
            raise ValueError("invalid item freshness threshold")
        for field in ("observation_ids", "event_ids", "source_ids"):
            if not isinstance(item[field], list) or any(not isinstance(x, str) for x in item[field]) or item[field] != sorted(set(item[field])):
                raise ValueError("invalid item freshness references")
        validate_freshness_contract(item)


def validate_scoped_evidence(artifact, supporting=()):
    """Recompute against real dependencies, not just self-declared ages."""
    if "freshness_items" in artifact and artifact["freshness_items"] != build_item_freshness(artifact, supporting):
        raise ValueError("item freshness does not match evidence dependencies")
