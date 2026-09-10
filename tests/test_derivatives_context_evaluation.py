import copy

import pytest

from test_derivatives_daily_context import fixture
from src.intelligence.daily_context import build_daily_context
from src.shadow.derivatives.consolidation import compose
from src.shadow.derivatives.context_evaluation import evaluate, validate_evaluation
from src.shadow.derivatives.validator import digest


def inputs():
    daily, up, b, f, o, cutoff = fixture()
    return b, build_daily_context(daily, *up, b, [f], [o], cutoff)


def test_available_evaluation_and_immutability():
    b, c = inputs()
    original = copy.deepcopy((b, c))
    r = evaluate(b, c)
    assert r["validation_status"] == "validated"
    assert r["status"] == "available"
    assert r["metrics"]["data_availability"]["value"] == 1
    assert r["metrics"]["missing_data_frequency"]["value"] == 0
    assert r["metrics"]["provenance_completeness"]["value"] == 1
    assert r["evidence_refs"] == sorted(f["evidence_id"] for f in b["evidence"])
    assert (b, c) == original
    assert validate_evaluation(r, b, c)
    r["status"] = "partial"
    assert not validate_evaluation(r, b, c)


@pytest.mark.parametrize("missing", [True, False])
def test_unavailable_provider(missing):
    daily, up, _, _, _, cutoff = fixture()
    b = None if missing else compose([], [], cutoff)
    c = build_daily_context(daily, *up, b, [], [], cutoff)
    r = evaluate(b, c)
    assert r["validation_status"] == "validated"
    assert r["status"] == "unavailable"
    assert r["metrics"]["data_availability"]["value"] == 0
    assert r["metrics"]["missing_data_frequency"]["value"] == 1
    assert r["metrics"]["freshness_success_rate"]["value"] is None


def test_stale_ratio_and_later_cutoff():
    b, c = inputs()
    r = evaluate(b, c)
    assert r["metrics"]["current_vs_stale"]["stale"]["value"] == .5
    assert r["metrics"]["freshness_success_rate"]["value"] == .5
    daily, up, b, f, o, _ = fixture()
    c = build_daily_context(daily, *up, b, [f], [o], "2026-09-11T00:02:00.123Z")
    r = evaluate(b, c)
    assert r["validation_status"] == "validated"
    assert r["metrics"]["current_vs_stale"]["stale"]["value"] == 1


@pytest.mark.parametrize("field", ["provenance", "timestamps", "source_records", "observations", "freshness"])
def test_context_provenance_corruption(field):
    b, c = inputs()
    c["derivatives_evidence"]["current_facts"][0][field] = {}
    r = evaluate(b, c)
    assert r["validation_status"] == "invalid"
    assert r["metrics"] is None


def test_broken_receipt_in_excluded_stale_evidence():
    b, c = inputs()
    stale_id = c["derivatives_evidence"]["excluded_evidence_refs"][0]
    fact = next(f for f in b["evidence"] if f["evidence_id"] == stale_id)
    fact["source_records"][0]["receipts"] = []
    c["derivatives_evidence"]["bundle_ref"]["artifact_hash"] = digest(b)
    assert evaluate(b, c)["validation_status"] == "invalid"


def test_missing_context_and_partial_coverage():
    assert evaluate(None, None)["validation_status"] == "invalid"
    daily, up, _, f, _, cutoff = fixture()
    b = compose([f], [], cutoff)
    c = build_daily_context(daily, *up, b, [f], [], cutoff)
    r = evaluate(b, c)
    assert r["status"] == "partial"
    assert r["metrics"]["missing_data_frequency"]["value"] == .5
