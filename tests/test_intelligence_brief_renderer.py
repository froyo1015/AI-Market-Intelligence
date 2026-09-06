from __future__ import annotations

import copy
import json
from datetime import timedelta
from pathlib import Path

import pytest

from src.brief.intelligence_renderer import render_daily_market_brief
from src.brief.renderer_pipeline import (
    BriefRendererInputError,
    run_renderer_pipeline,
)
from src.brief.renderer_validator import (
    BriefRendererValidationError,
    REFERENCE_KEYS,
    validate_rendered_brief,
    validate_renderer_input,
)
from src.intelligence.composer import build_daily_intelligence_artifact
from src.data.freshness import enrich_artifact_freshness
from src.top_intelligence.selector import build_top_intelligence_artifact
from tests.test_cross_asset_signals import NOW
from tests.test_daily_intelligence import _four_inputs
from tests.test_evidence_consolidation import _calendar


def _intelligence(*, stale_hours: int = 0, calendar: bool = False) -> dict:
    inputs = _four_inputs(calendar=_calendar() if calendar else None)
    return build_daily_intelligence_artifact(
        *inputs,
        now=NOW + timedelta(hours=stale_hours),
    ).to_dict()


def _top(artifact: dict) -> dict:
    return enrich_artifact_freshness(
        build_top_intelligence_artifact(artifact, now=NOW).to_dict(),
        supporting_artifacts=[artifact],
    )


def test_renders_complete_contract_sections_without_selecting_objects() -> None:
    artifact = _intelligence(calendar=True)
    result = render_daily_market_brief(artifact, _top(artifact))
    markdown = result.markdown

    assert result.schema_contract == "deterministic_brief_renderer_v1"
    assert result.source_run_id == artifact["run_id"]
    assert result.source_status == "available"
    for heading in (
        "# Daily Market Intelligence Brief",
        "# Today's Top Market Intelligence",
        "## Data Quality and Coverage",
        "## Current Market Regime",
        "## Cross-Asset Observations",
        "## Upcoming Event Risks",
        "## Data Quality Risks",
        "## Observed Market Stress",
        "## Sources and Provenance",
        "## Scope Limitations",
    ):
        assert heading in markdown
    assert markdown.count("- Signal ID:") == len(
        artifact["cross_asset_signals"]
    )
    assert markdown.count("- Risk ID:") == (
        len(artifact["upcoming_events"])
        + len(artifact["data_quality_risks"])
        + len(artifact["observed_market_stress"])
    )


def test_unavailable_input_preserves_warnings_and_quality_risks() -> None:
    artifact = _intelligence(stale_hours=25)
    result = render_daily_market_brief(artifact)

    assert result.source_status == "unavailable"
    assert "- Intelligence status: `unavailable`" in result.markdown
    for warning in artifact["warnings"]:
        assert f"- {warning}" in result.markdown
    for item in artifact["data_quality_risks"]:
        assert item["payload"]["risk_id"] in result.markdown
    assert "artifact_freshness_status" not in result.markdown
    assert "| stale |" in result.markdown


def test_every_object_reference_and_source_record_is_rendered() -> None:
    artifact = _intelligence(calendar=True)
    markdown = render_daily_market_brief(artifact).markdown
    objects = [artifact["market_regime"]]
    for section in (
        "cross_asset_signals",
        "upcoming_events",
        "data_quality_risks",
        "observed_market_stress",
    ):
        objects.extend(artifact[section])

    for obj in objects:
        assert obj["object_id"] in markdown
        assert obj["source_run_id"] in markdown
        assert obj["source_generated_at"] in markdown
        assert obj["validation_status"] in markdown
        for key in REFERENCE_KEYS:
            for reference in obj["evidence_refs"][key]:
                assert reference in markdown
    for source in artifact["provenance_catalog"]["source_records"]:
        assert source["source_id"] in markdown
        assert source["url"] in markdown


def test_same_input_produces_byte_identical_markdown() -> None:
    artifact = _intelligence(calendar=True)
    first = render_daily_market_brief(artifact)
    second = render_daily_market_brief(copy.deepcopy(artifact))

    assert first == second
    assert first.markdown.endswith("\n")
    validate_rendered_brief(first.markdown, artifact)


def test_validator_rejects_unvalidated_and_dangling_references() -> None:
    artifact = _intelligence()
    unvalidated = copy.deepcopy(artifact)
    unvalidated["cross_asset_signals"][0]["validation_status"] = "unchecked"
    with pytest.raises(BriefRendererValidationError, match="not validated"):
        validate_renderer_input(unvalidated)

    dangling = copy.deepcopy(artifact)
    dangling["cross_asset_signals"][0]["evidence_refs"]["evidence_ids"].append(
        "evd_missing"
    )
    dangling["cross_asset_signals"][0]["evidence_refs"]["evidence_ids"].sort()
    with pytest.raises(BriefRendererValidationError, match="unresolved evidence_ids"):
        validate_renderer_input(dangling)

    changed_status = copy.deepcopy(artifact)
    changed_status["cross_asset_signals"][0]["data_status"] = "stale_data"
    with pytest.raises(BriefRendererValidationError, match="status was changed"):
        validate_renderer_input(changed_status)


def test_output_validator_rejects_removed_warning_or_reference() -> None:
    artifact = _intelligence(stale_hours=25)
    markdown = render_daily_market_brief(artifact).markdown
    tampered = markdown.replace(
        f"- {artifact['warnings'][0]}\n",
        "",
        1,
    )
    with pytest.raises(
        BriefRendererValidationError,
        match="does not match deterministic rendering",
    ):
        validate_rendered_brief(tampered, artifact)


def test_pipeline_reads_one_artifact_and_writes_atomically(tmp_path: Path) -> None:
    artifact = _intelligence(calendar=True)
    input_path = tmp_path / "daily_intelligence.json"
    output_path = tmp_path / "daily_market_brief.md"
    top_path = tmp_path / "top_intelligence.json"
    input_path.write_text(json.dumps(artifact), encoding="utf-8")
    top_path.write_text(json.dumps(_top(artifact)), encoding="utf-8")

    result = run_renderer_pipeline(input_path, output_path, top_path)

    assert output_path.read_text(encoding="utf-8") == result.markdown
    assert not (tmp_path / "daily_market_brief.md.tmp").exists()

    bad_input = tmp_path / "bad.json"
    bad_input.write_text("[]", encoding="utf-8")
    with pytest.raises(BriefRendererInputError, match="root must be an object"):
        run_renderer_pipeline(bad_input, output_path)
