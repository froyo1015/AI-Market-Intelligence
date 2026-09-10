"""Artificial production-shaped inputs; never live market data."""

import copy
import hashlib
import json

import pytest

from src.shadow.derivatives.production_schema import ProductionObservation, ShadowObservationOutput
from src.shadow.derivatives.production_validator import content_hash, milliseconds, validate_output
from src.shadow.derivatives.validator import validate_artifact


def seal(a):
    for row in a["instruments"] + a["observations"]:
        row["content_hash"] = content_hash(row)
    return a


def example(metric="funding_rate"):
    definition = {
        "venue_id": "venue:example", "native_symbol": "BTCUSDT", "instrument_type": "perpetual",
        "base_asset_id": "asset:bitcoin", "quote_asset_id": "asset:usdt",
        "settlement_asset_id": "asset:usdt", "underlying_asset_id": "asset:bitcoin",
        "oi_unit": "base_asset", "counting_basis": "single_side", "funding_interval_seconds": 28800,
        "funding_rate_kind": "settled", "funding_sign_convention": "positive_long_pays_short",
        "effective_from": "2026-09-01T00:00:00.000Z", "effective_to": None,
    }
    stamp = "2026-09-09T00:00:00.123Z"
    value = "0.0001" if metric == "funding_rate" else "123"
    unit = "fraction_per_interval" if metric == "funding_rate" else "base_asset"
    raw = {}
    receipts = []
    for name, payload in (("metadata", definition), ("measurement", {
            "symbol": "BTCUSDT", "metric": metric, "value": value, "time": milliseconds(stamp)})):
        path = "outputs/shadow/derivatives/test-run/" + name + ".json"
        raw[path] = json.dumps(payload).encode()
        receipts.append({"receipt_id": "receipt:" + name, "source_id": "source:example",
                         "captured_at": "2026-09-09T00:00:01.123Z", "path": path,
                         "sha256": "sha256:" + hashlib.sha256(raw[path]).hexdigest()})
    o = {
        "schema_contract": "derivatives_production_observation_v1", "synthetic": False,
        "observation_id": "derivatives:observation:test", "version": 1,
        "instrument_ref": "instrument:btc@1", "receipt_ref": "receipt:measurement",
        "pointers": {"value": "/value", "timestamp": "/time", "symbol": "/symbol", "metric": "/metric"},
        "metric": metric, "value": value, "unit": unit,
        "native_timestamp": milliseconds(stamp), "native_time_unit": "ms", "source_timestamp": stamp,
        "retrieved_at": "2026-09-09T00:00:01.123Z", "generated_at": "2026-09-09T00:00:02.123Z",
        "known_at": "2026-09-09T00:00:01.123Z",
        "freshness": {"age_seconds": "2", "freshness_status": "current", "policy_id": "production-observation-freshness-v1"},
        "evidence_quality": {"policy_id": "production-observation-quality-v1", "data_reliability": 1,
                             "timeliness": 1, "temporal_coverage": 1, "definition_consistency": 1, "score": 1},
        "content_hash": "",
    }
    a = {
        "schema_contract": "derivatives_shadow_output_v1", "synthetic": False, "run_id": "test-run",
        "requested_cutoff": stamp, "evaluation_cutoff": "2026-09-09T00:00:02.123Z",
        "replay_mode": "archived_point_in_time",
        "sources": [{"source_id": "source:example", "venue_id": "venue:example",
                     "publisher": "Test only", "data_reliability": 1}],
        "receipts": receipts,
        "instruments": [{"instrument_id": "instrument:btc", "version": 1, "metadata_receipt_ref": "receipt:metadata",
                         "definition_pointer": "", "definition": definition, "content_hash": ""}],
        "observations": [o],
        "coverage": [{"instrument_ref": "instrument:btc@1", "metric": m,
                      "status": "available" if m == metric else "unavailable",
                      "reason": None if m == metric else "not_collected"}
                     for m in ("funding_rate", "open_interest", "liquidation_quantity", "long_short_ratio", "positioning_change")],
    }
    return seal(a), raw


def update_raw(a, raw, name, payload):
    receipt = next(r for r in a["receipts"] if r["receipt_id"] == "receipt:" + name)
    raw[receipt["path"]] = json.dumps(payload).encode()
    receipt["sha256"] = "sha256:" + hashlib.sha256(raw[receipt["path"]]).hexdigest()


@pytest.mark.parametrize("metric", ["funding_rate", "open_interest"])
def test_valid_contract(metric):
    a, raw = example(metric)
    result = validate_output(a, raw)
    assert result.valid, result.errors
    assert result.availability == "partial" and result.historical_availability == "pass"
    assert ProductionObservation(**a["observations"][0]).to_dict() == a["observations"][0]
    assert ShadowObservationOutput(**a).to_dict() == a


@pytest.mark.parametrize("mutation", [
    lambda a: a.update(synthetic=True),
    lambda a: a.update(schema_contract="derivatives_fixture_v2"),
    lambda a: a["observations"][0].update(synthetic=True),
    lambda a: a["observations"][0].update(source_timestamp="2026-09-09T00:00:00.000Z"),
    lambda a: a["observations"][0].update(source_timestamp="2026-09-09T00:00:00.1234Z"),
    lambda a: a["observations"][0].update(source_timestamp="2026-09-09T00:00:00Z"),
    lambda a: a["observations"][0].update(native_time_unit="us"),
    lambda a: a["observations"][0].update(native_timestamp=True),
    lambda a: a["observations"][0].update(value="0.5"),
    lambda a: a["observations"][0].update(instrument_ref="instrument:btc@99"),
    lambda a: a["observations"][0].update(known_at="2026-09-01T00:00:00.000Z"),
    lambda a: a["observations"][0]["pointers"].update(value="/absent"),
    lambda a: a["observations"][0]["pointers"].update(value="/~invalid"),
    lambda a: a["coverage"].pop(),
    lambda a: a.update(run_id="../escape"),
    lambda a: a["receipts"][0].update(path="src/output/metadata.json"),
    lambda a: a["receipts"][0].update(path="outputs/shadow/derivatives/test-run/../secret"),
    lambda a: a["instruments"][0]["definition"].update(counting_basis="guess"),
    lambda a: a["observations"][0].update(confidence=0.9),
])
def test_invalid_contract(mutation):
    a, raw = example()
    mutation(a)
    assert not validate_output(seal(a), raw).valid


def test_metadata_lookahead_and_backfill():
    a, raw = example()
    later = "2026-09-10T00:00:00.000Z"
    a["receipts"][0]["captured_at"] = later
    o = a["observations"][0]
    o.update(known_at=later, generated_at=later)
    assert not validate_output(seal(a), raw).valid
    a["replay_mode"] = "transformation_only"
    result = validate_output(a, raw)
    assert result.valid, result.errors
    assert result.historical_availability == "indeterminate"


def test_wrong_effective_revision():
    a, raw = example()
    d = a["instruments"][0]["definition"]
    d["effective_to"] = a["observations"][0]["source_timestamp"]
    update_raw(a, raw, "metadata", d)
    assert not validate_output(seal(a), raw).valid  # exclusive upper bound


def test_immutable_revision():
    a, raw = example()
    previous = copy.deepcopy(a)
    a["observations"][0]["generated_at"] = "2026-09-09T00:00:02.000Z"
    assert validate_output(seal(a), raw).valid
    assert not validate_output(a, raw, previous).valid
    a["observations"][0]["version"] = 2
    assert validate_output(seal(a), raw, previous).valid


def test_stale_and_unknown_reliability():
    a, raw = example()
    a["evaluation_cutoff"] = "2026-09-10T00:00:02.123Z"
    o = a["observations"][0]
    o["freshness"].update(age_seconds="86402", freshness_status="stale")
    o["evidence_quality"].update(timeliness=0, score=0)
    assert validate_output(seal(a), raw).valid
    a["sources"][0]["data_reliability"] = None
    o["evidence_quality"].update(data_reliability=None, score=None)
    assert validate_output(seal(a), raw).valid


def test_empty_unavailable_output():
    a, raw = example()
    a["observations"] = []
    for c in a["coverage"]:
        c.update(status="unavailable", reason="source_unavailable")
    result = validate_output(a, raw)
    assert result.valid and result.availability == "unavailable"


def test_raw_integrity_and_duplicate_keys():
    a, raw = example()
    path = a["receipts"][0]["path"]
    raw[path] += b" "
    assert not validate_output(a, raw).valid
    raw[path] = b'{"x":1,"x":2}'
    a["receipts"][0]["sha256"] = "sha256:" + hashlib.sha256(raw[path]).hexdigest()
    assert not validate_output(a, raw).valid


def test_millisecond_boundary_age():
    a, raw = example("open_interest")
    a["evaluation_cutoff"] = "2026-09-09T02:00:00.124Z"
    o = a["observations"][0]
    o["freshness"].update(age_seconds="7200.001", freshness_status="stale")
    o["evidence_quality"].update(timeliness=0, score=0)
    assert validate_output(seal(a), raw).valid


def test_native_seconds_not_truncated():
    a, raw = example()
    o = a["observations"][0]
    o.update(native_timestamp=o["native_timestamp"] // 1000, native_time_unit="s",
             source_timestamp="2026-09-09T00:00:00.000Z")
    o["freshness"]["age_seconds"] = "2.123"
    payload = json.loads(raw[a["receipts"][1]["path"]])
    payload["time"] = o["native_timestamp"]
    update_raw(a, raw, "measurement", payload)
    assert validate_output(seal(a), raw).valid


def test_deterministic_nonmutating_and_separation():
    a, raw = example()
    before = copy.deepcopy(a)
    assert validate_output(a, raw) == validate_output(a, raw)
    assert a == before
    assert not validate_artifact(a).valid


@pytest.mark.parametrize("a", [None, [], {}, 1])
def test_malformed(a):
    assert not validate_output(a, {}).valid
