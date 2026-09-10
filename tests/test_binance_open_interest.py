"""Offline provider-shaped OI fixtures; no live call in tests."""

import base64
import json

import pytest

from src.shadow.derivatives import binance_funding as shared
from src.shadow.derivatives.binance_open_interest import (
    BinanceOpenInterestAdapter, OpenInterestTransport, validate_adapter_artifact, write_shadow_artifact,
)
from src.shadow.derivatives.provider_security import ProviderRequest, validate_public_artifact, SecurityBoundaryError


class NoSecrets:
    def get(self, name):
        raise AssertionError("credential access forbidden")


class Transport:
    def __init__(self, overrides=None):
        self.calls = []
        self.data = {"exchange": {"symbols": [{"symbol": s, "contractType": "PERPETUAL",
                    "baseAsset": s[:-4], "quoteAsset": "USDT", "marginAsset": "USDT"} for s in shared.SYMBOLS]},
                    **{s: [{"symbol": s, "sumOpenInterest": "123.4500", "sumOpenInterestValue": "999999.00",
                            "timestamp": shared.milliseconds("2026-09-10T00:00:00.123Z")}]
                       for s in shared.SYMBOLS}}
        self.data.update(overrides or {})

    def get(self, name, cutoff, timeout):
        self.calls.append(name)
        x = self.data[name]
        if isinstance(x, Exception):
            raise x
        return x if isinstance(x, tuple) else (200, json.dumps(x).encode())


def run(overrides=None, **limits):
    t = Transport(overrides)
    a = BinanceOpenInterestAdapter("oi-test", t, clock=lambda: "2026-09-10T00:02:00.123Z",
                                   monotonic=lambda: 0, sleep=lambda _: None)
    a.collect(ProviderRequest(shared.PROVIDER, tuple(shared.REFS.values()), ("open_interest",), **limits), NoSecrets())
    return a.artifact, t


def test_success_identity_units_and_provenance():
    a, t = run()
    assert t.calls == ["exchange", "BTCUSDT", "ETHUSDT"]
    assert a["status"] == "available" and validate_adapter_artifact(a).valid
    for o, asset in zip(a["observation_output"]["observations"], ("bitcoin", "ethereum")):
        assert o["metric"] == "open_interest" and o["unit"] == "base_asset"
        assert o["value"] == "123.45"  # not quote notional, not doubled
        assert o["source_timestamp"] == "2026-09-10T00:00:00.123Z"
        i = next(i for i in a["observation_output"]["instruments"] if i["instrument_id"] + "@" + str(i["version"]) == o["instrument_ref"])
        assert i["definition"]["base_asset_id"] == "asset:" + asset
        assert i["definition"]["venue_id"] == "venue:binance-usdm"
        assert i["definition"]["funding_interval_seconds"] is None
    assert all(b["capture_refs"] == ["exchange", b["symbol"]] for b in a["normalization_receipts"])


@pytest.mark.parametrize("status", [401, 403, 418, 429, 451])
def test_provider_failure(status):
    a, t = run({"exchange": (status, b"secret-error-body")})
    assert len(t.calls) == 1 and a["status"] == "unavailable"
    assert validate_adapter_artifact(a).valid and "secret-error-body" not in json.dumps(a)


@pytest.mark.parametrize("value", ["NaN", "-1", None, 1.5, "1e3"])
def test_invalid_quantity(value):
    rows = Transport().data["BTCUSDT"]
    rows[0]["sumOpenInterest"] = value
    a, _ = run({"BTCUSDT": rows})
    assert a["status"] == "partial" and a["symbol_status"]["ETHUSDT"] == "available"


@pytest.mark.parametrize("timestamp", [True, "1788998400123", 1.5, 0, 9999999999999])
def test_invalid_timestamp(timestamp):
    rows = Transport().data["BTCUSDT"]
    rows[0]["timestamp"] = timestamp
    a, _ = run({"BTCUSDT": rows})
    assert a["symbol_status"]["BTCUSDT"] == "unavailable"


@pytest.mark.parametrize("bad", [[], {}, (200, b"broken-json"), {"code": -1, "msg": "do-not-log"}])
def test_malformed(bad):
    a, _ = run({"BTCUSDT": bad})
    assert a["status"] == "partial" and "do-not-log" not in json.dumps(a)


def test_timeout_budget():
    a, t = run({"BTCUSDT": TimeoutError("private")})
    assert t.calls.count("BTCUSDT") == 2 and a["status"] == "partial"
    assert "private" not in json.dumps(a)
    a, t = run(max_attempts=1)
    assert len(t.calls) == 1 and a["status"] == "unavailable"


def test_unit_mapping_fail_closed():
    exchange = Transport().data["exchange"]
    exchange["symbols"][0]["marginAsset"] = "BTC"
    a, _ = run({"exchange": exchange})
    assert a["symbol_status"]["BTCUSDT"] == "unavailable"
    a, _ = run()
    a["observation_output"]["observations"][0]["unit"] = "quote_asset"
    with pytest.raises(ValueError):
        validate_adapter_artifact(a)


def test_missing_quantity_not_substituted_by_notional():
    rows = Transport().data["BTCUSDT"]
    del rows[0]["sumOpenInterest"]
    a, _ = run({"BTCUSDT": rows})
    assert a["symbol_status"]["BTCUSDT"] == "unavailable"


def test_zero_and_stale():
    rows = Transport().data["BTCUSDT"]
    rows[0].update(sumOpenInterest="0.0000", timestamp=shared.milliseconds("2026-09-09T20:00:00.002Z"))
    a, _ = run({"BTCUSDT": rows})
    o = a["observation_output"]["observations"][0]
    assert o["value"] == "0" and o["freshness"]["freshness_status"] == "stale"
    assert validate_adapter_artifact(a).valid


def test_public_rejection_and_shadow_write(tmp_path, monkeypatch):
    a, _ = run({"exchange": (403, b"")})
    with pytest.raises(SecurityBoundaryError):
        validate_public_artifact("binance_oi_observations.json", a, {shared.PROVIDER})
    monkeypatch.setattr(shared, "ROOT", tmp_path / "shadow")
    path = write_shadow_artifact(a)
    assert path.name == "binance_oi_observations.json"
    assert json.loads(path.read_text())["status"] == "unavailable"
    with pytest.raises(FileExistsError):
        write_shadow_artifact(a)


def test_tampering():
    a, _ = run()
    a["captures"]["BTCUSDT"]["body_base64"] = base64.b64encode(b"[]").decode()
    with pytest.raises(ValueError):
        validate_adapter_artifact(a)


def test_fixed_query_and_determinism():
    q = OpenInterestTransport().query("BTCUSDT", 100000000)
    assert q["period"] == "1h" and q["limit"] == 30 and q["endTime"] == 100000000
    assert run()[0] == run()[0]
