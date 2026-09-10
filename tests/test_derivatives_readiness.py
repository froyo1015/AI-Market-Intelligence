import copy

import pytest

from test_binance_funding_adapter import FakeTransport, NoSecrets
from test_binance_open_interest import Transport
from tests.test_daily_intelligence import _four_inputs, _compose
from src.shadow.derivatives.binance_funding import BinanceFundingAdapter, PROVIDER, REFS
from src.shadow.derivatives.binance_open_interest import BinanceOpenInterestAdapter
from src.shadow.derivatives.provider_security import ProviderRequest
from src.shadow.derivatives.production_validator import milliseconds
from src.shadow.derivatives.consolidation import compose
from src.intelligence.daily_context import build_daily_context
from src.shadow.derivatives.readiness import assess, validate_readiness

AS_OF = "2026-09-10T00:03:00.123Z"


def sample(day, archive_request=False):
    stamp = f"2026-09-{day:02d}T00:02:00.123Z"
    t = milliseconds(f"2026-09-{day:02d}T00:00:00.123Z")
    ft = FakeTransport({s: [{"symbol": s, "fundingTime": ts, "fundingRate": "0.0001"}
                           for ts in (t - 28800000, t)] for s in REFS})
    ot = Transport({s: [{"symbol": s, "sumOpenInterest": "123.45", "sumOpenInterestValue": "999999",
                         "timestamp": t}] for s in REFS})
    artifacts = []
    for cls, transport, metric in ((BinanceFundingAdapter, ft, "funding_rate"),
                                    (BinanceOpenInterestAdapter, ot, "open_interest")):
        a = cls(f"fixture-{day}", transport, clock=lambda: stamp, monotonic=lambda: 0, sleep=lambda _: None)
        a.collect(ProviderRequest(PROVIDER, tuple(REFS.values()), (metric,)), NoSecrets())
        artifacts.append(a.artifact)
    f, o = artifacts
    b = compose([f], [o], stamp)
    up = _four_inputs()
    if archive_request:
        return {"funding": [f], "oi": [o], "daily": _compose(up), "upstream": list(up),
                "cutoff": stamp, "archived_at": stamp}
    c = build_daily_context(_compose(up), *up, b, [f], [o], stamp)
    return {"bundle": b, "context": c}


def test_insufficient_history_and_duplicate_prevention():
    p = sample(10)
    r = assess([p] * 7, AS_OF)
    assert r["status"] == "insufficient_history"
    assert r["history"]["unique_sample_count"] == 1
    assert r["history"]["duplicate_count"] == 6
    assert assess([], AS_OF)["status"] == "insufficient_history"


def test_passing_readiness_is_review_only_and_deterministic():
    history = [sample(d) for d in range(4, 11)]
    original = copy.deepcopy(history)
    r = assess(history, AS_OF)
    assert r["status"] == "passing", r
    assert all(r["checks"].values())
    assert r["production_enabled"] is False
    assert r == assess(list(reversed(history)), AS_OF)
    assert validate_readiness(r, history, AS_OF)
    assert history == original


def test_missing_provenance():
    p = sample(10)
    p["context"]["derivatives_evidence"]["current_facts"][0]["provenance"] = {}
    r = assess([p], AS_OF)
    assert r["status"] == "blocked"
    assert not r["checks"]["provenance"]


def test_stale_data():
    from test_derivatives_context_evaluation import inputs
    b, c = inputs()
    r = assess([{"bundle": b, "context": c}], AS_OF)
    assert r["status"] == "blocked"
    assert not r["checks"]["freshness"]


def test_unavailable_provider():
    up = _four_inputs()
    c = build_daily_context(_compose(up), *up, None, [], [], AS_OF)
    r = assess([{"bundle": None, "context": c}], AS_OF)
    assert r["status"] == "blocked"
    assert not r["checks"]["availability"]


@pytest.mark.parametrize("field", ["prediction", "api_key", "raw_response"])
def test_safety_constraints(field):
    p = sample(10)
    p["context"]["derivatives_evidence"][field] = "test-only"
    r = assess([p], AS_OF)
    assert r["status"] == "blocked" and not r["checks"]["safety"]
    assert "test-only" not in str(r)


def test_future_and_reused_history_rejected():
    p = sample(10)
    assert assess([p], "2026-09-09T00:03:00.123Z")["status"] == "blocked"
    q = copy.deepcopy(p)
    q["context"]["derivatives_evidence"]["evaluated_at"] = AS_OF
    assert assess([p, q], AS_OF)["status"] == "blocked"
