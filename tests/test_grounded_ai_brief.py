from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.grounded_brief.llm_adapter import GroundedLLMAdapterError
from src.grounded_brief.pipeline import run_grounded_brief_pipeline
from src.grounded_brief.prompt_builder import (
    INPUT_END_MARKER,
    INPUT_START_MARKER,
    build_grounded_brief_prompt,
)
from src.grounded_brief.validator import (
    GroundedBriefValidationError,
    validate_grounded_brief,
)
from src.models.generation_metadata_schema import (
    GenerationMetadataValidationError,
    validate_generation_metadata,
)
from tests.test_evidence_consolidation import _calendar
from tests.test_top_intelligence import RISK_OFF_VALUES, _daily, _top


class StaticAdapter:
    provider_name = "static_test_writer"

    def __init__(self, response: str) -> None:
        self.response = response

    def generate(self, prompt: str) -> str:
        assert INPUT_START_MARKER in prompt
        assert INPUT_END_MARKER in prompt
        return self.response


class FailingAdapter:
    provider_name = "failing_test_writer"

    def generate(self, prompt: str) -> str:
        del prompt
        raise GroundedLLMAdapterError("provider timeout")


def _inputs() -> tuple[dict, dict]:
    daily = _daily(values=RISK_OFF_VALUES, calendar=_calendar())
    return _top(daily), daily


def _all_refs(item: dict) -> list[str]:
    values = [item["item_id"]]
    values.extend(item["source_refs"])
    for refs in item["evidence_refs"].values():
        values.extend(refs)
    values.append(item["source_object_id"])
    return list(dict.fromkeys(str(value) for value in values if value))


def _cite(values: list[str]) -> str:
    return "[refs: " + ", ".join(values) + "]"


def _valid_brief(top: dict, daily: dict) -> str:
    lines = [
        "# Daily Market Intelligence Brief",
        "",
        "## Today's Top 3",
        "",
    ]
    for item in top["items"]:
        refs = _all_refs(item)
        compact = refs[:4]
        lines.extend(
            (
                f"### {item['rank']}. {item['headline']}",
                f"{item['why']} {_cite(compact)}",
                f"Why it matters: This is a current validated priority. {_cite(compact)}",
                f"Watch next: {item['monitor']} {_cite(compact)}",
                "Source / Evidence: " + ", ".join(compact),
                "",
            )
        )

    regime = daily["market_regime"]
    regime_refs = [regime["object_id"], regime["source_run_id"]]
    lines.extend(
        (
            "## Market Regime",
            "",
            f"The current validated regime is {regime['payload']['classification']}. {_cite(regime_refs)}",
            "",
            "## Cross-Asset Signals",
            "",
        )
    )
    observed_signal = next(
        item
        for item in daily["cross_asset_signals"]
        if item["payload"]["state"] == "observed"
    )
    signal_refs = [
        observed_signal["payload"]["signal_id"],
        observed_signal["source_run_id"],
    ]
    lines.extend(
        (
            f"{observed_signal['payload']['label']} is observed in the validated input. {_cite(signal_refs)}",
            "",
            "## Risks & Next 48 Hours",
            "",
        )
    )
    event = daily["upcoming_events"][0]
    event_name = event["payload"]["observed_facts"]["name"]
    event_refs = [
        event["payload"]["risk_id"],
        event["payload"]["observed_facts"]["event_id"],
    ]
    lines.extend(
        (
            f"{event_name} is present in the validated upcoming-event window. {_cite(event_refs)}",
            "",
            "## Data Quality",
            "",
            f"No validated data-quality risk is present in this input. {_cite([daily['run_id']])}",
        )
    )
    return "\n".join(lines).rstrip() + "\n"


def test_valid_grounded_brief_and_prompt_contract() -> None:
    top, daily = _inputs()
    prompt = build_grounded_brief_prompt(top, daily)
    brief = _valid_brief(top, daily)

    assert INPUT_START_MARKER in prompt and INPUT_END_MARKER in prompt
    assert top["items"][0]["headline"] in prompt
    validate_grounded_brief(brief, top, daily)


def test_hallucinated_asset_is_rejected() -> None:
    top, daily = _inputs()
    brief = _valid_brief(top, daily).replace(
        "The current validated regime",
        "MSFT and the current validated regime",
    )
    with pytest.raises(GroundedBriefValidationError, match="asset-like symbol"):
        validate_grounded_brief(brief, top, daily)


def test_hallucinated_event_is_rejected() -> None:
    top, daily = _inputs()
    brief = _valid_brief(top, daily).replace(
        "No validated data-quality risk is present",
        "An emergency FOMC meeting is present and no validated data-quality risk is present",
    )
    with pytest.raises(GroundedBriefValidationError, match="event mention"):
        validate_grounded_brief(brief, top, daily)


def test_unsupported_number_is_rejected() -> None:
    top, daily = _inputs()
    brief = _valid_brief(top, daily).replace(
        "This is a current validated priority.",
        "This is a current validated priority with value 987654321.",
        1,
    )
    with pytest.raises(GroundedBriefValidationError, match="numerical value"):
        validate_grounded_brief(brief, top, daily)


def test_unsupported_causal_claim_is_rejected() -> None:
    top, daily = _inputs()
    brief = _valid_brief(top, daily).replace(
        "This is a current validated priority.",
        "The dollar caused this current condition.",
        1,
    )
    with pytest.raises(GroundedBriefValidationError, match="prohibited"):
        validate_grounded_brief(brief, top, daily)


def test_prediction_language_is_rejected() -> None:
    top, daily = _inputs()
    brief = _valid_brief(top, daily).replace(
        "This is a current validated priority.",
        "Gold will fall.",
        1,
    )
    with pytest.raises(GroundedBriefValidationError, match="prohibited"):
        validate_grounded_brief(brief, top, daily)


def test_missing_citation_is_rejected() -> None:
    top, daily = _inputs()
    brief = _valid_brief(top, daily).replace(
        "No validated data-quality risk is present in this input. "
        + _cite([daily["run_id"]]),
        "No validated data-quality risk is present in this input.",
    )
    with pytest.raises(GroundedBriefValidationError, match="missing citation"):
        validate_grounded_brief(brief, top, daily)


def test_llm_failure_copies_deterministic_fallback(tmp_path: Path) -> None:
    top, daily = _inputs()
    result, output, fallback = _run_pipeline(
        tmp_path,
        top,
        daily,
        FailingAdapter(),
    )

    assert result.mode == "fallback"
    assert result.generation_mode == "deterministic_fallback"
    assert result.generation_status == "fallback"
    assert result.freshness_status == daily.get("freshness_status", "unknown")
    assert result.validation_status == "validated"
    assert result.provider == "failing_test_writer"
    assert result.fallback_reason == "provider_timeout"
    assert result.failure_type == "GroundedLLMAdapterError"
    assert result.generation_metadata()["fallback_reason"] == "provider_timeout"
    assert output.read_bytes() == fallback.read_bytes()


def test_invalid_llm_output_uses_same_deterministic_fallback(tmp_path: Path) -> None:
    top, daily = _inputs()
    result, output, fallback = _run_pipeline(
        tmp_path,
        top,
        daily,
        StaticAdapter("# Daily Market Intelligence Brief\nGold will fall.\n"),
    )

    assert result.mode == "fallback"
    assert result.generation_mode == "deterministic_fallback"
    assert result.generation_status == "fallback"
    assert result.provider == "static_test_writer"
    assert result.fallback_reason == "invalid_llm_output"
    assert result.failure_type == "GroundedBriefValidationError"
    assert output.read_bytes() == fallback.read_bytes()


def test_valid_llm_output_is_written_and_repeated_fallback_is_deterministic(
    tmp_path: Path,
) -> None:
    top, daily = _inputs()
    brief = _valid_brief(top, daily)
    generated, output, fallback = _run_pipeline(
        tmp_path,
        top,
        daily,
        StaticAdapter(brief),
    )
    assert generated.mode == "generated"
    assert generated.generation_mode == "grounded_ai"
    assert generated.generation_status == "success"
    assert generated.validation_status == "validated"
    assert generated.provider == "static_test_writer"
    assert generated.fallback_reason is None
    assert generated.generation_metadata()["generation_mode"] == "grounded_ai"
    assert output.read_text(encoding="utf-8") == brief

    first, output, fallback = _run_pipeline(
        tmp_path,
        top,
        daily,
        FailingAdapter(),
    )
    first_bytes = output.read_bytes()
    second, output, _ = _run_pipeline(
        tmp_path,
        top,
        daily,
        FailingAdapter(),
    )
    assert first.mode == second.mode == "fallback"
    assert first_bytes == output.read_bytes() == fallback.read_bytes()


def test_no_provider_configured_has_explicit_public_fallback_metadata(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    top, daily = _inputs()
    result, output, fallback = _run_pipeline(tmp_path, top, daily, None)

    assert result.generation_mode == "deterministic_fallback"
    assert result.generation_status == "fallback"
    assert result.provider is None
    assert result.fallback_reason == "no_provider_configured"
    assert result.validation_status == "validated"
    assert output.read_bytes() == fallback.read_bytes()
    assert set(result.generation_metadata()) == {
        "generation_mode",
        "generation_status",
        "generated_at",
        "freshness_status",
        "validation_status",
        "provider",
        "fallback_reason",
    }


def test_generation_metadata_rejects_unapproved_public_fields(tmp_path: Path) -> None:
    top, daily = _inputs()
    result, _, _ = _run_pipeline(tmp_path, top, daily, None)
    metadata = result.generation_metadata()
    metadata["raw_provider_response"] = "secret response"

    with pytest.raises(
        GenerationMetadataValidationError,
        match="unsupported fields",
    ):
        validate_generation_metadata(metadata)


def _run_pipeline(
    tmp_path: Path,
    top: dict,
    daily: dict,
    adapter,
):
    top_path = tmp_path / "top_intelligence.json"
    daily_path = tmp_path / "daily_intelligence.json"
    fallback_path = tmp_path / "daily_market_brief.md"
    output_path = tmp_path / "ai_market_brief.md"
    top_path.write_text(json.dumps(top), encoding="utf-8")
    daily_path.write_text(json.dumps(daily), encoding="utf-8")
    fallback_path.write_text(
        "# Daily Market Intelligence Brief\n\nDeterministic fallback.\n",
        encoding="utf-8",
    )
    result = run_grounded_brief_pipeline(
        top_path,
        daily_path,
        fallback_path,
        output_path,
        adapter,
    )
    return result, output_path, fallback_path
