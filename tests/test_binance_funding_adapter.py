import copy
import json

import pytest

from src.shadow.derivatives.binance_funding import (
    BinanceFundingAdapter, PROVIDER, REFS, validate_adapter_artifact, milliseconds,
)
from src.shadow.derivatives.provider_security import ProviderRequest, validate_public_artifact, SecurityBoundaryError


class NoSecrets:
    def get(self, name):
        raise AssertionError("must not access credentials")


class FakeTransport:
    def __init__(self, overrides=None):
        self.calls = []
        t = milliseconds("2026-09-09T00:00:00.123Z")
        self.responses = {
            "exchange": {"symbols": [{"symbol": s, "contractType": "PERPETUAL", "baseAsset": s[:-4],
                                        "quoteAsset": "USDT", "marginAsset": "USDT"} for s in REFS]},
            "intervals": [],
            **{s: [{"symbol": s, "fundingTime": ts, "fundingRate": "0.00010000"}
                   for ts in (t - 28800000, t)] for s in REFS},
        }
        self.responses.update(overrides or {})

    def get(self, name, cutoff, timeout):
        self.calls.append(name)
        result = self.responses[name]
        if isinstance(result, Exception):
            raise result
        if isinstance(result, tuple):
            return result
        return 200, json.dumps(result).encode()


def run(overrides=None, **limits):
    transport = FakeTransport(overrides)
    adapter = BinanceFundingAdapter("test", transport, clock=lambda: "2026-09-09T00:02:00.123Z",
                                    monotonic=lambda: 0, sleep=lambda _: None)
    adapter.collect(ProviderRequest(PROVIDER, tuple(REFS.values()), ("funding_rate",), **limits), NoSecrets())
    return adapter.artifact, transport


def test_success_schema_provenance_and_precision():
    a, transport = run()
    assert a["status"] == "available" and len(transport.calls) == 4
    assert validate_adapter_artifact(a).valid
    for o in a["observation_output"]["observations"]:
        assert o["source_timestamp"].endswith(".123Z")
        assert o["value"] == "0.0001"
        assert o["synthetic"] is False
        assert o["known_at"] == a["evaluation_cutoff"]
    assert len(a["normalization_receipts"]) == 4


@pytest.mark.parametrize("status", [403, 429, 418, 451, 401])
def test_provider_unavailable_circuit(status):
    a, t = run({"exchange": (status, b"private-error-body")})
    assert a["status"] == "unavailable" and len(t.calls) == 1
    assert a["observation_output"]["observations"] == []
    assert validate_adapter_artifact(a).valid
    assert "private-error-body" not in json.dumps(a)


@pytest.mark.parametrize("bad", [(200, b"not json"), {"code": -1, "msg": "private-message"},
                                  [{"symbol": "BTCUSDT", "fundingTime": True, "fundingRate": "1"}]])
def test_malformed_isolation(bad):
    a, _ = run({"BTCUSDT": bad})
    assert a["status"] == "partial"
    assert a["symbol_status"]["ETHUSDT"] == "available"
    assert validate_adapter_artifact(a).valid
    assert "private-message" not in json.dumps(a)


def test_timeout_retry_is_bounded():
    a, t = run({"BTCUSDT": TimeoutError("sensitive")})
    assert t.calls.count("BTCUSDT") == 2
    assert a["status"] == "partial" and "sensitive" not in json.dumps(a)


def test_budget():
    a, t = run(max_attempts=1)
    assert len(t.calls) == 1 and a["status"] == "unavailable"


def test_reject_normalization_tampering():
    a, _ = run()
    a["observation_output"]["observations"][0]["value"] = "123"
    with pytest.raises(ValueError):
        validate_adapter_artifact(a)


def test_reject_raw_tampering():
    a, _ = run()
    a["captures"]["exchange"]["body_base64"] = "e30="
    with pytest.raises(ValueError):
        validate_adapter_artifact(a)


def test_shadow_not_public():
    a, _ = run()
    with pytest.raises(SecurityBoundaryError):
        validate_public_artifact("binance_funding_observations.json", a, {PROVIDER})


def test_interval_conflict_unavailable():
    a, _ = run({"intervals": [{"symbol": "BTCUSDT", "fundingIntervalHours": 4}]})
    assert a["status"] == "partial"


@pytest.mark.parametrize("jitter,accepted", [(-2, True), (1000, True), (-1000, True), (1001, False), (-1001, False)])
def test_live_settlement_jitter(jitter, accepted):
    rows = FakeTransport().responses["BTCUSDT"]
    rows[-1]["fundingTime"] += jitter
    a, _ = run({"BTCUSDT": rows})
    assert (a["symbol_status"]["BTCUSDT"] == "available") == accepted
    if accepted:
        o = a["observation_output"]["observations"][0]
        assert o["native_timestamp"] == rows[-1]["fundingTime"]
        assert validate_adapter_artifact(a).valid


def test_deterministic():
    assert run()[0] == run()[0]


def test_write_unavailable_shadow(tmp_path, monkeypatch):
    from src.shadow.derivatives import binance_funding as module
    monkeypatch.setattr(module, "ROOT", tmp_path / "shadow")
    a, _ = run({"exchange": (403, b"")})
    path = module.write_shadow_artifact(a)
    assert json.loads(path.read_text())["status"] == "unavailable"
    assert path.parent.name == "test"
    with pytest.raises(FileExistsError):
        module.write_shadow_artifact(a)


def test_wrong_contract_and_future_timestamp():
    bad = FakeTransport().responses
    bad["exchange"]["symbols"][0]["contractType"] = "CURRENT_QUARTER"
    a, _ = run({"exchange": bad["exchange"]})
    assert a["symbol_status"]["BTCUSDT"] == "unavailable"
    bad["ETHUSDT"][-1]["fundingTime"] += 999999999
    a, _ = run({"ETHUSDT": bad["ETHUSDT"]})
    assert a["symbol_status"]["ETHUSDT"] == "unavailable"
