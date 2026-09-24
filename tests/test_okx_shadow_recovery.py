import copy
import json
import subprocess
from pathlib import Path

import pytest

from src.shadow.derivatives import okx, binance_funding, providers, recovery
from src.shadow.derivatives.provider_security import ProviderRequest
from src.shadow.derivatives.consolidation import compose
from src.shadow.derivatives.production_validator import milliseconds
from src.shadow.derivatives.scheduler import run, fact_index
from src.shadow.derivatives.archive import replay
from src.intelligence import evidence_boundary
from test_binance_funding_adapter import NoSecrets, run as binance_fixture
from test_derivatives_readiness import sample

STAMP = "2026-09-10T00:02:00.123Z"
SETTLED = milliseconds("2026-09-10T00:00:00.123Z")


class Transport:
    def __init__(self, metric, overrides=None):
        self.calls = []
        self.responses = {}
        for s in okx.SYMBOLS:
            base = s.split("-")[0]
            self.responses["metadata-" + s] = {"code": "0", "data": [{
                "instId": s, "instType": "SWAP", "ctType": "linear", "settleCcy": "USDT",
                "uly": base + "-USDT", "ctValCcy": base, "ctVal": "0.01", "ctMult": "1", "state": "live"}]}
            self.responses["schedule-" + s] = {"code": "0", "data": [{"instId": s,
                "fundingTime": str(SETTLED + 28800000), "nextFundingTime": str(SETTLED + 57600000)}]}
            self.responses[s] = {"code": "0", "data": ([{"instId": s, "instType": "SWAP",
                "fundingTime": str(t), "realizedRate": "0.00010000", "fundingRate": "0.9876"}
                for t in (SETTLED - 28800000, SETTLED)] if metric == "funding_rate" else [
                    {"instId": s, "instType": "SWAP", "oi": "25000.5", "oiCcy": "250.005",
                     "oiUsd": "12345678.9", "ts": str(SETTLED + 1000)}])}
        self.responses.update(overrides or {})

    def get(self, name, cutoff, timeout):
        self.calls.append(name)
        value = self.responses[name]
        if isinstance(value, Exception):
            raise value
        return value if isinstance(value, tuple) else (200, json.dumps(value).encode())


def collect(metric="funding_rate", overrides=None, stamp=STAMP, clock=None, **limits):
    transport = Transport(metric, overrides)
    cls = okx.OKXFundingAdapter if metric == "funding_rate" else okx.OKXOpenInterestAdapter
    a = cls("okx-fixture-" + metric, transport, clock=clock or (lambda: stamp),
            monotonic=lambda: 0, sleep=lambda _: None)
    a.collect(ProviderRequest("okx", tuple(okx.REFS.values()), (metric,), **limits), NoSecrets())
    return a.artifact, transport


@pytest.mark.parametrize("metric", ["funding_rate", "open_interest"])
def test_okx_complete_identity_precision_units_and_private_provenance(metric):
    a, _ = collect(metric)
    assert a["status"] == "available" and okx.validate_adapter_artifact(a).valid
    for o in a["observation_output"]["observations"]:
        assert o["source_timestamp"].endswith(".123Z")
        assert o["instrument_ref"].startswith("instrument:okx-")
        assert o["unit"] == ("fraction_per_interval" if metric == "funding_rate" else "contracts")
        assert o["value"] == ("0.0001" if metric == "funding_rate" else "25000.5")
        assert o["freshness"]["freshness_status"] == "current"
    assert all(s["source_id"] == "source:okx" for s in a["observation_output"]["receipts"])
    assert all(i["definition"]["venue_id"] == "venue:okx" for i in a["observation_output"]["instruments"])
    assert a == collect(metric)[0]


@pytest.mark.parametrize("response,code", [((403, b"secret-body"), "access_denied"),
    ((429, b"secret-body"), "rate_limited"), ({"code": "50011", "msg": "secret-body"}, "rate_limited")])
def test_denial_or_cooldown_stops_requests_without_body_leak(response, code):
    a, t = collect(overrides={"metadata-BTC-USDT-SWAP": response})
    assert len(t.calls) == 1 and a["status"] == "unavailable"
    assert code in a["failures"].values() and "secret-body" not in json.dumps(a)
    assert okx.validate_adapter_artifact(a).valid


@pytest.mark.parametrize("metric", ["funding_rate", "open_interest"])
def test_one_bad_symbol_does_not_block_other_symbol(metric):
    a, _ = collect(metric, {"BTC-USDT-SWAP": (200, b"not-json")})
    assert a["status"] == "partial" and a["symbol_status"]["ETH-USDT-SWAP"] == "available"


def test_rate_prediction_never_substitutes_for_settled_funding():
    data = Transport("funding_rate").responses["BTC-USDT-SWAP"]
    data["data"][-1]["realizedRate"] = ""
    a, _ = collect(overrides={"BTC-USDT-SWAP": data})
    assert a["symbol_status"]["BTC-USDT-SWAP"] == "unavailable"


@pytest.mark.parametrize("field,value", [("oi", "-1"), ("oi", "NaN"), ("ts", "1788998400"),
                                        ("ts", str(SETTLED + 999999999)), ("instId", "BTC-USD-SWAP")])
def test_oi_bad_unit_identity_or_timestamp_rejected(field, value):
    data = Transport("open_interest").responses["BTC-USDT-SWAP"]
    data["data"][0][field] = value
    a, _ = collect("open_interest", {"BTC-USDT-SWAP": data})
    assert a["symbol_status"]["BTC-USDT-SWAP"] == "unavailable"


def test_oi_after_collection_start_is_not_backdated():
    ticks = iter(["2026-09-10T00:00:00.123Z"] + [STAMP] * 10)
    a, _ = collect("open_interest", clock=lambda: next(ticks))
    assert a["status"] == "available"
    assert a["requested_cutoff"] == STAMP
    assert a["collection_started_at"] < a["observation_output"]["observations"][0]["source_timestamp"]


def test_source_newer_than_its_measurement_receipt_rejected():
    ticks = iter(["2026-09-10T00:00:00.123Z"] * 5 + [STAMP])
    a, _ = collect("open_interest", clock=lambda: next(ticks))
    assert a["status"] == "unavailable"


def test_stale_not_promoted():
    a, _ = collect(stamp="2026-09-11T00:02:00.123Z")
    assert all(o["freshness"]["freshness_status"] == "stale" for o in a["observation_output"]["observations"])


def test_timeout_retry_bounded_and_no_error_text():
    a, t = collect(overrides={"BTC-USDT-SWAP": TimeoutError("private")})
    assert t.calls.count("BTC-USDT-SWAP") == 2 and "private" not in json.dumps(a)


def test_raw_or_normalized_tamper_rejected():
    a, _ = collect()
    a["observation_output"]["observations"][0]["value"] = "100"
    with pytest.raises(ValueError):
        okx.validate_adapter_artifact(a)


def test_cross_venue_bundle_rejected_instead_of_averaged():
    a, _ = collect("open_interest")
    with pytest.raises(ValueError, match="venue"):
        compose([binance_fixture()[0]], [a], STAMP)
    with pytest.raises(ValueError):
        providers.validate_source(a, "funding_rate")


def test_okx_archive_continuity_dedup_and_rights_closed_publication(tmp_path, monkeypatch):
    monkeypatch.setattr(evidence_boundary, "SHADOW_ROOT", tmp_path)
    req = sample(10, archive_request=True)
    from test_derivatives_scheduler import Collected
    f, oi = collect()[0], collect("open_interest")[0]
    for name, stamp in (("first", STAMP), ("second", "2026-09-10T00:03:00.123Z")):
        run(tmp_path / "history", tmp_path / name, req["daily"], req["upstream"], name,
            clock=lambda: stamp, adapters=[Collected(f), Collected(oi)])
    entries = [json.loads(p.read_text()) for p in (tmp_path / "history").glob("*/*.json")]
    assert len(entries) == 2 and all(replay(e)["bundle"]["status"] == "available" for e in entries)
    assert len(fact_index(tmp_path / "history")["facts"]) == 4
    p = json.loads((tmp_path / "second/derivatives-recovery-proof.json").read_text())
    assert recovery.validate_proof(p) and p["archive"]["prior_entries_preserved"]
    assert len(p["archive"]["before_entry_hashes"]) == 1 and len(p["archive"]["after_entry_hashes"]) == 2
    assert all(r["provider"] == "okx" and r["provenance_validated"] for r in p["observations"])
    public = json.loads((tmp_path / "second/derivatives-shadow.json").read_text())
    assert all(r["value"] is None for r in public["measurements"])
    assert public["readiness"]["production_enabled"] is False
    for forbidden in ("body_base64", "normalized_bytes", "headers", "0.0001", "25000.5", str(tmp_path)):
        assert forbidden not in json.dumps(p) + json.dumps(public)
    for extra in ("raw_response", "secret", "value", "receipt"):
        bad = copy.deepcopy(p)
        bad["observations"][0][extra] = "not-public"
        with pytest.raises(ValueError):
            recovery.validate_proof(bad)


def test_checkpoint_order_uses_creation_time_not_numeric_id():
    script = """
    const {orderCheckpoints} = require('./src/shadow/derivatives/checkpoint_order.cjs');
    const a = {id: 10795666983, created_at: '2026-09-24T07:28:51Z', workflow_run: {head_branch: 'main'}};
    const b = {id: 10795204597, created_at: '2026-09-24T07:32:49Z', workflow_run: {head_branch: 'main'}};
    const wrong = {...b, id: 1, workflow_run: {head_branch: 'other'}};
    if (orderCheckpoints([a,b,wrong], 'main').map(x=>x.id).join() !== [b.id,a.id].join()) process.exit(1);
    try { orderCheckpoints([{...a,created_at:'bad'}], 'main'); process.exit(2); } catch(e) {}
    """
    subprocess.run(["node", "-e", script], check=True)
    workflow = Path(".github/workflows/derivatives_shadow.yml").read_text()
    assert "orderCheckpoints(artifacts, branch)" in workflow
    assert "run.conclusion === 'success'" in workflow
    assert "--provider" in workflow and "derivatives-recovery-proof.json" in workflow
