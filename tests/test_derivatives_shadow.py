"""Offline shadow contracts; fixture values are not market data."""

import copy
import json
from pathlib import Path

import pytest

from src.shadow.derivatives.schema import DerivativesObservationV2, DerivativesEvidenceV2
from src.shadow.derivatives.validator import digest, record_hash, validate_artifact

FIXTURES = Path(__file__).parent / "fixtures/shadow/derivatives"


def load(name="complete"):
    return json.loads((FIXTURES / (name + ".json")).read_text())


def seal(a):
    for s in a["sources"]:
        s["raw_hash"] = digest(s["raw_payload"])
    for r in a["observations"] + a["evidence"]:
        r["content_hash"] = record_hash(r)
    return a


def sync_raw(a):
    """Test-only explicit raw fixture correction, never validator repair."""
    for s in a["sources"]:
        s["raw_payload"]["measurements"] = [
            {"instrument_ref": r["instrument_ref"], "payload": copy.deepcopy(r["payload"]),
             "observed_at": r["timestamps"]["observed_at"]}
            for r in a["observations"] if not r["observation_refs"] and
            s["source_id"] + "@" + str(s["version"]) in r["source_refs"]]
    return seal(a)


@pytest.mark.parametrize("name", ["complete", "missing"])
def test_fixtures(name):
    result = validate_artifact(load(name))
    assert result.valid, result.errors
    assert result.audit["result"] == "pass"


def test_model_roundtrip_and_families():
    a = load()
    for r in a["observations"]:
        assert DerivativesObservationV2(**r).to_dict() == r
    for r in a["evidence"]:
        assert DerivativesEvidenceV2(**r).to_dict() == r
    assert len({r["payload"]["metric"] for r in a["observations"]}) == 5


@pytest.mark.parametrize("field,value", [
    ("value", "NaN"), ("value", "Infinity"), ("value", "0.00"),
    ("value", "-0"), ("value", 0.01), ("unit", "unknown"),
    ("interval_seconds", True), ("sign_convention", "bullish"),
])
def test_bad_funding_payload(field, value):
    a = load()
    a["observations"][0]["payload"][field] = value
    assert not validate_artifact(seal(a)).valid


@pytest.mark.parametrize("mutation", [
    lambda a: a["observations"][0].update(schema_contract="v999"),
    lambda a: a["observations"][0].update(source_refs=["source:absent@1"]),
    lambda a: a["observations"][0].update(related_assets=["asset:equity"]),
    lambda a: a["observations"][0].update(instrument_ref="instrument:absent@1"),
    lambda a: a["observations"][0].update(confidence=1),
    lambda a: a["observations"].append(copy.deepcopy(a["observations"][0])),
    lambda a: a["evidence"][0].update(claim_type="bullish"),
    lambda a: a["evidence"][0]["payload"].update(value="0.99"),
    lambda a: a["observations"][-1]["payload"].update(value="99"),
    lambda a: a["observations"][1]["payload"].update(counting_basis="unknown"),
    lambda a: a["observations"][3]["payload"].update(value="0", coverage_fraction=0.5),
    lambda a: a["instruments"][1]["token"].update(redemption_ratio="1"),
    lambda a: a["coverage"].pop(),
    lambda a: a["coverage"][0].update(status="unavailable", missing_reason="not_collected"),
])
def test_closed_contract_rejection(mutation):
    a = load()
    mutation(a)
    assert not validate_artifact(seal(a)).valid


def test_hash_tampering():
    a = load()
    a["observations"][0]["payload"]["value"] = "0.2"
    assert "record hash mismatch" in validate_artifact(a).errors
    a = load()
    a["sources"][0]["raw_payload"]["fixture"] = "tampered"
    assert "raw hash mismatch" in validate_artifact(a).errors


def test_stale_without_regeneration_refresh():
    a = load("missing")
    a["cutoff"] = "2026-09-10T00:02:00Z"
    for r in a["observations"] + a["evidence"]:
        r["freshness"].update(age_seconds=86520, freshness_status="stale")
        r["evidence_quality"]["components"]["timeliness"] = 0
        r["evidence_quality"]["score"] = 0
    assert validate_artifact(seal(a)).valid
    a["observations"][0]["freshness"]["freshness_status"] = "current"
    assert not validate_artifact(seal(a)).valid


def test_unknown_reliability():
    a = load("missing")
    a["sources"][0]["data_reliability"] = None
    for r in a["observations"] + a["evidence"]:
        r["evidence_quality"]["components"]["data_reliability"] = None
        r["evidence_quality"]["score"] = None
    assert validate_artifact(seal(a)).valid
    a["evidence"][0]["evidence_quality"]["score"] = 1
    assert not validate_artifact(seal(a)).valid


def test_unknown_freshness():
    a = load()
    a["observations"] = [a["observations"][2]]
    a["evidence"] = []
    for c in a["coverage"]:
        c.update(status="available" if c["metric"] == "open_interest" else "unavailable",
                 missing_reason=None if c["metric"] == "open_interest" else "not_collected")
    r = a["observations"][0]
    r["timestamps"]["observed_at"] = None
    r["freshness"].update(source_timestamp=None, age_seconds=None, freshness_status="unknown")
    r["evidence_quality"]["components"]["timeliness"] = None
    r["evidence_quality"]["score"] = None
    assert validate_artifact(sync_raw(a)).valid


def test_pit_backfill():
    a = load("missing")
    a["sources"][0]["retrieved_at"] = "2026-09-10T00:01:00Z"
    for r in a["observations"] + a["evidence"]:
        r["known_at"] = "2026-09-10T00:01:00Z"
        for obj in (r["timestamps"], r["freshness"]):
            obj.update(retrieved_at="2026-09-10T00:01:00Z", generated_at="2026-09-10T00:02:00Z")
    assert not validate_artifact(seal(a)).valid
    a["replay_mode"] = "transformation_only"
    result = validate_artifact(a)
    assert result.valid, result.errors
    assert result.audit["historical_availability"] == "indeterminate"


def test_preserves_all_sources_and_conflicts():
    a = load("missing")
    source = copy.deepcopy(a["sources"][0])
    source["source_id"] = "source:second"
    a["sources"].append(source)
    second = copy.deepcopy(a["observations"][0])
    second.update(record_id="derivatives:observation:second", source_refs=["source:second@1"])
    a["observations"].append(second)
    claim = a["evidence"][0]
    claim["observation_refs"].append("derivatives:observation:second@1")
    claim["source_refs"].append("source:second@1")
    assert validate_artifact(seal(a)).valid
    claim["source_refs"].pop()
    assert not validate_artifact(seal(a)).valid
    a["evidence"] = []
    second["payload"]["value"] = "0.0002"
    assert validate_artifact(sync_raw(a)).valid  # conflicts retained, not merged


def test_rehashed_but_ungrounded_measurement():
    a = load("missing")
    for r in a["observations"] + a["evidence"]:
        r["payload"]["value"] = "0.005"
    assert "measurement not grounded in raw fixture" in validate_artifact(seal(a)).errors


def test_cycle_and_cross_instrument():
    a = load()
    a["observations"][-1]["observation_refs"] = ["derivatives:observation:positioning@1"]
    assert not validate_artifact(seal(a)).valid
    a = load()
    a["observations"][1]["instrument_ref"] = "instrument:token-perp@1"
    assert not validate_artifact(seal(a)).valid


def test_deterministic_nonmutating_and_audit():
    a = load()
    before = copy.deepcopy(a)
    one, two = validate_artifact(a), validate_artifact(a)
    assert one == two and a == before
    assert one.audit["known_at"] == "2026-09-09T00:01:00Z"
    assert one.audit["run_id"] == "synthetic-phase-a"
    a["observations"].reverse()
    a["evidence"].reverse()
    assert validate_artifact(a).valid
    assert {r["content_hash"] for r in a["observations"]} == {r["content_hash"] for r in before["observations"]}


def test_all_unavailable_creates_no_evidence():
    a = load("missing")
    a["observations"] = []
    a["evidence"] = []
    a["sources"] = []
    for c in a["coverage"]:
        c.update(status="unavailable", missing_reason="source_unavailable")
    result = validate_artifact(a)
    assert result.valid and result.audit["known_at"] is None


def test_revision_pinning():
    a = load("missing")
    a["observations"][0]["record_version"] = 2
    assert not validate_artifact(seal(a)).valid
    a["evidence"][0]["observation_refs"] = ["derivatives:observation:funding@2"]
    assert validate_artifact(seal(a)).valid


def test_future_observation_rejected():
    a = load("missing")
    a["observations"][0]["timestamps"]["observed_at"] = "2026-09-10T00:00:00Z"
    assert not validate_artifact(seal(a)).valid


def test_funding_freshness_boundary():
    a = load("missing")
    a["cutoff"] = "2026-09-09T08:30:00Z"
    for r in a["observations"] + a["evidence"]:
        r["freshness"]["age_seconds"] = 30600
    assert validate_artifact(seal(a)).valid
    a["cutoff"] = "2026-09-09T08:30:01Z"
    assert not validate_artifact(a).valid


@pytest.mark.parametrize("value", [None, [], 42, {}, {"synthetic": True}])
def test_malformed_top_level(value):
    assert not validate_artifact(value).valid


def test_no_production_imports_or_publication():
    root = Path(__file__).parents[1]
    for p in (root / "src").rglob("*.py"):
        if "shadow" not in p.relative_to(root / "src").parts and p != root / "src/intelligence/evidence_boundary.py":
            assert "src.shadow" not in p.read_text()
    assert "shadow.derivatives" not in (root / "pyproject.toml").read_text()
    for p in (root / ".github/workflows").glob("*.yml"):
        if p.name == "derivatives_shadow.yml":
            # Phase 8.1 permits isolated scheduling, never raw/public publication.
            text = p.read_text()
            assert "upload-pages-artifact" not in text
            assert text.count("uses: actions/upload-artifact") == 2
            upload = text.split("- name: Persist ciphertext only")[1]
            assert "path: outputs/shadow/derivatives/scheduled/checkpoint.gpg" in upload
            assert "path: outputs/shadow/derivatives/scheduled/run/derivatives-shadow.json" in upload
            continue
        assert "shadow/derivatives" not in p.read_text()
