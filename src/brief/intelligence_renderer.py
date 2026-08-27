"""Deterministically render validated daily intelligence as Markdown."""

from __future__ import annotations

import json
from typing import Any, List, Mapping, Sequence

from src.brief.renderer_validator import REFERENCE_KEYS, validate_renderer_input
from src.models.brief_renderer_schema import DeterministicBrief


REFERENCE_LABELS = {
    "artifact_run_ids": "Artifact runs",
    "evidence_bundle_ids": "Evidence bundles",
    "source_ids": "Sources",
    "observation_ids": "Observations",
    "event_ids": "Events",
    "evidence_ids": "Evidence",
    "signal_ids": "Signals",
    "regime_dimension_ids": "Regime dimensions",
    "risk_ids": "Risks",
    "coverage_inputs": "Coverage inputs",
}
CATALOG_FIELDS = (
    ("evidence_bundles", "id", "Evidence bundles"),
    ("source_records", "source_id", "Sources"),
    ("observation_records", "observation_id", "Observations"),
    ("event_records", "event_id", "Events"),
    ("evidence_records", "evidence_id", "Evidence records"),
)


def render_daily_market_brief(
    artifact: Mapping[str, Any],
) -> DeterministicBrief:
    validate_renderer_input(artifact)
    lines: List[str] = [
        "# Daily Market Intelligence Brief",
        "",
        f"- Report date: {_inline(artifact['report_date'])}",
        f"- Intelligence status: `{_inline(artifact['status'])}`",
        f"- Intelligence run: `{_inline(artifact['run_id'])}`",
        f"- Intelligence generated at: {_inline(artifact['generated_at'])}",
        f"- Input contract: `{_inline(artifact['schema_contract'])}`",
        "- Render mode: `deterministic_structured_only`",
        "",
        "## Data Quality and Coverage",
        "",
        *_render_coverage(artifact["coverage"]),
        "",
        "### Data Quality Warnings",
        "",
        *_bullet_values(artifact["warnings"]),
        "",
        "### Data Windows",
        "",
        *_render_data_windows(artifact["data_window"]),
        "",
        "## Current Market Regime",
        "",
        *_render_regime(artifact["market_regime"]),
        "",
        "## Cross-Asset Observations",
        "",
        *_render_signal_section(artifact["cross_asset_signals"]),
        "",
        "## Upcoming Event Risks",
        "",
        *_render_risk_section(artifact["upcoming_events"]),
        "",
        "## Data Quality Risks",
        "",
        *_render_risk_section(artifact["data_quality_risks"]),
        "",
        "## Observed Market Stress",
        "",
        *_render_risk_section(artifact["observed_market_stress"]),
        "",
        "## Sources and Provenance",
        "",
        *_render_provenance(artifact),
        "",
        "## Scope Limitations",
        "",
        *_bullet_values(artifact["limitations"]),
    ]
    markdown = "\n".join(lines).rstrip() + "\n"
    return DeterministicBrief(
        source_run_id=str(artifact["run_id"]),
        report_date=str(artifact["report_date"]),
        source_generated_at=str(artifact["generated_at"]),
        source_status=str(artifact["status"]),
        markdown=markdown,
    )


def _render_coverage(coverage: Sequence[Mapping[str, Any]]) -> List[str]:
    lines = [
        "| Artifact | Run / generated at | Validation | Data | "
        "Record freshness | Artifact freshness | Age / max hours | "
        "Objects | Warnings |",
        "|---|---|---|---|---|---|---:|---:|---:|",
    ]
    for item in coverage:
        lines.append(
            "| "
            + " | ".join(
                (
                    _table(item.get("artifact")),
                    (
                        f"`{_table(item.get('run_id'))}`<br>"
                        f"{_table(item.get('generated_at'))}"
                    ),
                    _table(item.get("validation_status")),
                    _table(item.get("data_status")),
                    _table(item.get("freshness_status")),
                    _table(item.get("artifact_freshness_status")),
                    (
                        f"{_table(item.get('age_hours'))} / "
                        f"{_table(item.get('maximum_age_hours'))}"
                    ),
                    _table(item.get("object_count")),
                    _table(item.get("warning_count")),
                )
            )
            + " |"
        )
    return lines


def _render_data_windows(data_window: Mapping[str, Any]) -> List[str]:
    lines = [
        f"- Composed at: {_inline(data_window.get('composed_at'))}",
        f"- Report date: {_inline(data_window.get('report_date'))}",
    ]
    for key in (
        "input_generated_at",
        "observed_at",
        "scheduled_at",
        "occurred_at",
        "published_at",
        "retrieved_at",
        "detected_at",
    ):
        window = data_window.get(key, {})
        lines.append(
            f"- {key}: {_inline(window.get('earliest'))} → "
            f"{_inline(window.get('latest'))}"
        )
    return lines


def _render_regime(obj: Mapping[str, Any]) -> List[str]:
    payload = obj["payload"]
    confidence = payload.get("confidence", {})
    lines = [
        f"- Classification: `{_inline(payload.get('classification'))}`",
        f"- Classification scope: {_inline(payload.get('classification_scope'))}",
        f"- Artifact status: `{_inline(payload.get('status'))}`",
        f"- Confidence label: `{_inline(confidence.get('label'))}`",
        f"- Confidence score: {_inline(confidence.get('score'))}",
        "",
        "### Regime Dimensions",
        "",
    ]
    dimensions = payload.get("dimensions", [])
    if not dimensions:
        lines.append("- None in validated input.")
    for dimension in dimensions:
        lines.extend(
            (
                f"- `{_inline(dimension.get('dimension_id'))}`: "
                f"eligibility=`{_inline(dimension.get('eligibility'))}`, "
                f"observed_state=`{_inline(dimension.get('observed_state'))}`, "
                f"signal=`{_inline(dimension.get('signal_id'))}`",
            )
        )
    lines.extend(
        (
            "",
            "Regime warnings:",
            "",
            *_bullet_values(payload.get("warnings", [])),
            "",
            *_render_limitations(payload.get("limitations", [])),
            *_render_common_object(obj),
        )
    )
    return lines


def _render_signal_section(objects: Sequence[Mapping[str, Any]]) -> List[str]:
    if not objects:
        return ["- None in validated input."]
    lines: List[str] = []
    for obj in objects:
        payload = obj["payload"]
        lines.extend(
            (
                f"### {_inline(payload.get('label'))}",
                "",
                f"- Signal ID: `{_inline(payload.get('signal_id'))}`",
                f"- Rule ID: `{_inline(payload.get('rule_id'))}`",
                f"- Relationship: `{_inline(payload.get('relationship_kind'))}`",
                f"- State: `{_inline(payload.get('state'))}`",
                f"- Condition met: `{_inline(payload.get('condition_met'))}`",
                f"- Data quality: `{_inline(payload.get('data_quality', {}).get('status'))}`",
                f"- Confidence: `{_inline(payload.get('confidence', {}).get('label'))}` "
                f"({_inline(payload.get('confidence', {}).get('score'))})",
                "",
                "Data-quality details:",
                "",
                *_render_mapping(payload.get("data_quality", {})),
                "",
                "Observed values:",
                "",
                *_render_observed_values(payload.get("observed_values", [])),
                "",
                *_render_limitations(payload.get("limitations", [])),
                *_render_common_object(obj),
                "",
            )
        )
    return _trim_blank(lines)


def _render_observed_values(values: Sequence[Mapping[str, Any]]) -> List[str]:
    if not values:
        return ["- None in validated input."]
    return [
        (
            f"- `{_inline(item.get('asset'))}` "
            f"{_inline(item.get('metric'))}={_inline(item.get('value'))} "
            f"{_inline(item.get('unit'))}; as_of={_inline(item.get('as_of'))}; "
            f"observation=`{_inline(item.get('observation_id'))}`; "
            f"source=`{_inline(item.get('source_id'))}`"
        )
        for item in values
    ]


def _render_risk_section(objects: Sequence[Mapping[str, Any]]) -> List[str]:
    if not objects:
        return ["- None in validated input."]
    lines: List[str] = []
    for obj in objects:
        payload = obj["payload"]
        lines.extend(
            (
                f"### {_inline(payload.get('title'))}",
                "",
                f"- Risk ID: `{_inline(payload.get('risk_id'))}`",
                f"- Rule ID: `{_inline(payload.get('rule_id'))}`",
                f"- Category: `{_inline(payload.get('category'))}`",
                f"- Status: `{_inline(payload.get('status'))}`",
                f"- Attention level: `{_inline(payload.get('attention_level'))}`",
                f"- Description: {_inline(payload.get('description'))}",
                f"- Related assets: {_inline(payload.get('related_assets'))}",
                "",
                "Observed facts:",
                "",
                *_render_mapping(payload.get("observed_facts", {})),
                "",
                "Time window:",
                "",
                *_render_mapping(payload.get("time_window", {})),
                "",
                *_render_limitations(payload.get("limitations", [])),
                *_render_common_object(obj),
                "",
            )
        )
    return _trim_blank(lines)


def _render_common_object(obj: Mapping[str, Any]) -> List[str]:
    lines = [
        "<details><summary>Traceability</summary>",
        "",
        "Object metadata:",
        "",
        f"- Object ID: `{_inline(obj.get('object_id'))}`",
        f"- Object type: `{_inline(obj.get('object_type'))}`",
        f"- Source artifact: `{_inline(obj.get('source_artifact'))}`",
        f"- Source run: `{_inline(obj.get('source_run_id'))}`",
        f"- Source generated at: {_inline(obj.get('source_generated_at'))}",
        f"- Validation status: `{_inline(obj.get('validation_status'))}`",
        f"- Data status: `{_inline(obj.get('data_status'))}`",
    ]
    timestamps = obj["timestamps"]
    for key in ("observed_at", "scheduled_at", "detected_at"):
        lines.append(f"- {key}: {_inline(timestamps[key])}")
    lines.extend(("", "Evidence references:", ""))
    refs = obj["evidence_refs"]
    for key in REFERENCE_KEYS:
        lines.append(f"- {REFERENCE_LABELS[key]}: {_code_values(refs[key])}")
    lines.extend(("", "</details>"))
    return lines


def _render_provenance(artifact: Mapping[str, Any]) -> List[str]:
    catalog = artifact["provenance_catalog"]
    lines = ["### Input Runs", ""]
    for key, value in artifact["input_refs"].items():
        lines.append(f"- {_inline(key)}: `{_inline(value)}`")
    lines.extend(("", "### Source Registry", ""))
    sources = catalog["source_records"]
    if not sources:
        lines.append("- None in validated input.")
    for source in sources:
        lines.extend(
            (
                f"- `{_inline(source.get('source_id'))}` — "
                f"{_inline(source.get('publisher'))}: "
                f"{_inline(source.get('title'))}",
                f"  - URL: {_inline(source.get('url'))}",
                f"  - Published at: {_inline(source.get('published_at'))}",
                f"  - Retrieved at: {_inline(source.get('retrieved_at'))}",
                f"  - Quality tier: {_inline(source.get('quality_tier'))}",
            )
        )
    lines.extend(("", "### Provenance Catalog IDs", ""))
    for catalog_key, id_key, label in CATALOG_FIELDS:
        identifiers = [item[id_key] for item in catalog[catalog_key]]
        lines.append(f"- {label}: {_code_values(identifiers)}")
    return lines


def _render_mapping(value: Mapping[str, Any]) -> List[str]:
    if not value:
        return ["- None in validated input."]
    return [f"- {_inline(key)}: {_inline(value[key])}" for key in sorted(value)]


def _render_limitations(values: Sequence[Any]) -> List[str]:
    return [
        "Limitations:",
        "",
        *_bullet_values(values),
        "",
    ]


def _bullet_values(values: Sequence[Any]) -> List[str]:
    if not values:
        return ["- None in validated input."]
    return [f"- {_inline(item)}" for item in values]


def _code_values(values: Sequence[Any]) -> str:
    if not values:
        return "none"
    return ", ".join(f"`{_inline(item)}`" for item in values)


def _inline(value: Any) -> str:
    if value is None:
        return "unknown"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (dict, list, tuple)):
        text = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    else:
        text = str(value)
    return " ".join(text.splitlines()).replace("\\", "\\\\").replace("|", "\\|")


def _table(value: Any) -> str:
    return _inline(value)


def _trim_blank(lines: List[str]) -> List[str]:
    while lines and lines[-1] == "":
        lines.pop()
    return lines
