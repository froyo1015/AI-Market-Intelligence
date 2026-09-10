import copy
import base64
import hashlib
import json
import pytest

from test_binance_funding_adapter import run as funding_run
from test_binance_open_interest import run as oi_run
from src.shadow.derivatives.consolidation import compose, validate_bundle
from src.shadow.derivatives import binance_funding as funding

AS_OF = "2026-09-10T00:02:00.123Z"


def test_complete_and_preserves_time_windows():
    f, o = funding_run()[0], oi_run()[0]
    b = compose([f], [o], AS_OF)
    assert b["status"] == "available" and len(b["evidence"]) == 4
    assert len(b["groups"]) == 4  # different UTC dates, not falsely aligned
    assert validate_bundle(b, [f], [o])


@pytest.mark.parametrize("missing", ["funding", "oi"])
def test_missing(missing):
    f = [] if missing == "funding" else [funding_run()[0]]
    o = [] if missing == "oi" else [oi_run()[0]]
    b = compose(f, o, AS_OF)
    assert b["status"] == "partial"
    assert sum(c["status"] == "unavailable" for c in b["coverage"]) == 2


def test_stale_quality_does_not_refresh():
    f = funding_run()[0]
    b = compose([f], [], AS_OF)
    for fact in b["evidence"]:
        assert fact["freshness"]["freshness_status"] == "stale"
        assert fact["evidence_quality"]["score"] == 0
        assert fact["source_records"][0]["observation"]["freshness"]["freshness_status"] == "current"


def test_provenance_and_tampering():
    f = funding_run()[0]
    b = compose([f], [], AS_OF)
    record = b["evidence"][0]["source_records"][0]
    assert record["captures"]["exchange"]["sha256"] == f["captures"]["exchange"]["sha256"]
    assert "body_base64" not in record["captures"]["exchange"]
    assert record["observation"] in f["observation_output"]["observations"]
    record["receipts"][0]["sha256"] = "wrong"
    assert not validate_bundle(b, [f], [])


def test_duplicate_artifacts_and_refetches():
    f = funding_run()[0]
    assert compose([f, f], [], AS_OF) == compose([f], [], AS_OF)
    # Different run with same fact: one evidence item, both provenance records.
    again = funding.assemble("second", f["requested_cutoff"], f["evaluation_cutoff"], f["captures"], f["fetch_failures"])
    b = compose([f, again], [], AS_OF)
    assert len(b["evidence"]) == 2
    assert all(len(x["source_records"]) == 2 for x in b["evidence"])
    assert b == compose([again, f], [], AS_OF)


def test_empty_and_unavailable_inputs():
    b = compose([], [], AS_OF)
    assert b["status"] == b["freshness_status"] == "unavailable"
    unavailable = funding_run({"exchange": (403, b"")})[0]
    assert compose([unavailable], [], AS_OF)["evidence"] == []


def test_cutoff_and_invalid_input():
    f = funding_run()[0]
    with pytest.raises(ValueError):
        compose([f], [], "2026-09-01T00:00:00.000Z")
    f["observation_output"]["observations"][0]["value"] = "fake"
    with pytest.raises(ValueError):
        compose([f], [], AS_OF)


def test_no_mutation():
    f = funding_run()[0]
    before = copy.deepcopy(f)
    compose([f], [], AS_OF)
    assert f == before


def test_same_day_link_and_conflicting_values():
    f = funding_run()[0]
    captures = copy.deepcopy(f["captures"])
    for name, c in captures.items():
        c["captured_at"] = AS_OF
        if name in funding.SYMBOLS:
            rows = json.loads(base64.b64decode(c["body_base64"]))
            for row in rows:
                row["fundingTime"] += 86400000
            body = json.dumps(rows).encode()
            c.update(body_base64=base64.b64encode(body).decode(), sha256="sha256:" + hashlib.sha256(body).hexdigest())
    f = funding.assemble("same-day", AS_OF, AS_OF, captures, {})
    b = compose([f], [oi_run()[0]], AS_OF)
    assert len(b["groups"]) == 2
    assert all(len(g["evidence_refs"]) == 2 for g in b["groups"])
    captures = copy.deepcopy(captures)
    c = captures["BTCUSDT"]
    rows = json.loads(base64.b64decode(c["body_base64"]))
    rows[-1]["fundingRate"] = "0.0002"
    body = json.dumps(rows).encode()
    c.update(body_base64=base64.b64encode(body).decode(), sha256="sha256:" + hashlib.sha256(body).hexdigest())
    conflict = funding.assemble("conflict", AS_OF, AS_OF, captures, {})
    b = compose([f, conflict], [], AS_OF)
    assert len(b["evidence"]) == 3
    assert sum(x["conflict"] for x in b["evidence"]) == 2
