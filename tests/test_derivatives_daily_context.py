import copy
import re
import json

import pytest

from tests.test_daily_intelligence import _four_inputs, _compose
from test_binance_funding_adapter import run as funding_run
from test_binance_open_interest import run as oi_run
from src.shadow.derivatives.consolidation import compose
from src.intelligence.daily_context import build_daily_context, validate_daily_context


def fixture():
    upstream = _four_inputs()
    f, o = funding_run()[0], oi_run()[0]
    cutoff = o["evaluation_cutoff"]
    bundle = compose([f], [o], cutoff)
    daily = _compose(upstream)
    return daily, upstream, bundle, f, o, cutoff


def test_available_context_and_stale_exclusion():
    daily, up, bundle, f, o, cutoff = fixture()
    result = build_daily_context(daily, *up, bundle, [f], [o], cutoff)
    section = result["derivatives_evidence"]
    assert section["status"] == "available"
    assert len(section["current_facts"]) == 2 and len(section["excluded_evidence_refs"]) == 2
    assert all(r["observations"][0]["metric"] == "open_interest" for r in section["current_facts"])
    assert result["daily_intelligence"] == daily
    assert validate_daily_context(result, *up, bundle, [f], [o])


def test_current_funding_is_included():
    daily, up, _, f, _, _ = fixture()
    cutoff = f["evaluation_cutoff"]
    b = compose([f], [], cutoff)
    r = build_daily_context(daily, *up, b, [f], [], cutoff)
    assert r["derivatives_evidence"]["status"] == "partial"
    assert all(x["observations"][0]["metric"] == "funding_rate" for x in r["derivatives_evidence"]["current_facts"])


@pytest.mark.parametrize("bundle", [None, {}])
def test_unavailable(bundle):
    daily, up, _, _, _, cutoff = fixture()
    r = build_daily_context(daily, *up, bundle, [], [], cutoff)
    assert r["derivatives_evidence"]["status"] == "unavailable"
    assert r["derivatives_evidence"]["current_facts"] == []
    assert r["daily_intelligence"] == daily


def test_reference_preservation():
    daily, up, b, f, o, cutoff = fixture()
    r = build_daily_context(daily, *up, b, [f], [o], cutoff)
    for fact in r["derivatives_evidence"]["current_facts"]:
        original = next(x for x in b["evidence"] if x["evidence_id"] == fact["id"])
        assert fact["source_records"] == original["source_records"]
        assert fact["provenance"]["observation_refs"] == original["observation_refs"]
        assert fact["freshness"] == original["freshness"]


def test_existing_writer_prompt_unchanged():
    from tests.test_top_intelligence import _top
    from src.grounded_brief.prompt_builder import build_grounded_brief_prompt

    daily, up, b, f, o, cutoff = fixture()
    top = _top(daily)
    before = build_grounded_brief_prompt(top, daily)
    context = build_daily_context(daily, *up, b, [f], [o], cutoff)
    assert build_grounded_brief_prompt(top, context["daily_intelligence"]) == before


def test_no_directional_fields_or_aliasing():
    daily, up, b, f, o, cutoff = fixture()
    before = copy.deepcopy(daily)
    r = build_daily_context(daily, *up, b, [f], [o], cutoff)
    assert not re.search(r'"(?:bullish|bearish|sentiment|prediction|trading_signal|recommendation)"', json.dumps(r["derivatives_evidence"]))
    r["derivatives_evidence"]["current_facts"][0]["bullish"] = True
    assert not validate_daily_context(r, *up, b, [f], [o])
    assert daily == before
