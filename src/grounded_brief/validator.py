"""Reject any generated brief that cannot be grounded mechanically."""

from __future__ import annotations

import re
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Set, Tuple

from src.grounded_brief.prompt_builder import build_grounding_registry


REQUIRED_HEADINGS = (
    "# Daily Market Intelligence Brief",
    "## Today's Top 3",
    "## Market Regime",
    "## Cross-Asset Signals",
    "## Risks & Next 48 Hours",
    "## Data Quality",
)
CITATION_PATTERN = re.compile(r"\[refs:\s*([^\]]+)\]\s*$")
SOURCE_LINE_PATTERN = re.compile(r"^Source / Evidence:\s*(.+)$")
ASSET_PATTERN = re.compile(r"\b[A-Z][A-Z0-9]*(?:-[A-Z0-9]+)?\b")
NUMBER_PATTERN = re.compile(r"(?<![A-Za-z_])-?\d+(?:\.\d+)?")
EVENT_CUE_PATTERN = re.compile(
    r"\b(?:CPI|FOMC|PCE|NFP|GDP|payrolls?|jobs report|rate decision|"
    r"emergency meeting|economic release)\b|(?:議息|非農|通脹報告|緊急會議)",
    re.IGNORECASE,
)
ALLOWED_UPPERCASE_WORDS = {
    "AI", "API", "CPI", "FOMC", "GDP", "ID", "LLM", "NFP", "PCE",
    "US", "U", "S", "UTC",
}
PROHIBITED_PATTERNS = (
    re.compile(r"\b(?:caused?|because of|led to|driven by|resulted in)\b", re.I),
    re.compile(r"(?:導致|造成|推動|因為)"),
    re.compile(r"\b(?:will|expected|likely|forecast|predict(?:s|ed|ion)?)\b", re.I),
    re.compile(r"(?:預計|將會|勢必|看漲|看跌)"),
    re.compile(r"\b(?:bullish|bearish|buy|sell|hold|price target|target price)\b", re.I),
    re.compile(r"(?:買入|賣出|持有建議|目標價|交易建議)"),
)
MAX_OUTPUT_CHARACTERS = 20_000


class GroundedBriefValidationError(ValueError):
    """Raised when generated Markdown violates grounding or safety rules."""


def validate_grounded_brief(
    markdown: str,
    top_intelligence: Mapping[str, Any],
    daily_intelligence: Mapping[str, Any],
) -> None:
    if not isinstance(markdown, str) or not markdown.strip():
        raise GroundedBriefValidationError("generated brief is empty")
    if len(markdown) > MAX_OUTPUT_CHARACTERS:
        raise GroundedBriefValidationError("generated brief exceeds size limit")
    if re.search(r"<\/?[A-Za-z][^>]*>|```", markdown):
        raise GroundedBriefValidationError("HTML and code fences are prohibited")
    for pattern in PROHIBITED_PATTERNS:
        if pattern.search(markdown):
            raise GroundedBriefValidationError("prohibited causal, predictive, or trading language")

    lines = markdown.splitlines()
    _validate_heading_order(lines)
    registry = build_grounding_registry(top_intelligence, daily_intelligence)
    allowed_refs = set(registry["allowed_reference_ids"])
    allowed_assets = set(registry["allowed_assets"])
    allowed_numbers = set(registry["allowed_numerical_tokens"])
    event_records = {
        str(item["event_id"]): str(item["name"])
        for item in registry["allowed_events"]
    }
    citations_by_line = _validate_lines_and_references(lines, allowed_refs)
    _validate_top_blocks(lines, citations_by_line, top_intelligence)
    _validate_section_references(lines, citations_by_line, daily_intelligence)
    _validate_assets(markdown, allowed_assets)
    _validate_events(lines, citations_by_line, event_records)
    _validate_numbers(lines, allowed_numbers)


def _validate_heading_order(lines: Sequence[str]) -> None:
    positions: List[int] = []
    for heading in REQUIRED_HEADINGS:
        matches = [index for index, line in enumerate(lines) if line == heading]
        if len(matches) != 1:
            raise GroundedBriefValidationError(f"heading must appear exactly once: {heading}")
        positions.append(matches[0])
    if positions != sorted(positions):
        raise GroundedBriefValidationError("required headings are out of order")


def _validate_lines_and_references(
    lines: Sequence[str],
    allowed_refs: Set[str],
) -> Dict[int, Set[str]]:
    citations: Dict[int, Set[str]] = {}
    for index, raw_line in enumerate(lines):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        source_match = SOURCE_LINE_PATTERN.fullmatch(line)
        citation_match = CITATION_PATTERN.search(line)
        if source_match:
            refs = _parse_refs(source_match.group(1))
        elif citation_match:
            refs = _parse_refs(citation_match.group(1))
        else:
            raise GroundedBriefValidationError(
                f"factual line is missing citation: line {index + 1}"
            )
        if not refs:
            raise GroundedBriefValidationError("citation block cannot be empty")
        unknown = refs - allowed_refs
        if unknown:
            raise GroundedBriefValidationError(
                f"unknown citation reference: {', '.join(sorted(unknown))}"
            )
        citations[index] = refs
    return citations


def _validate_top_blocks(
    lines: Sequence[str],
    citations: Mapping[int, Set[str]],
    top: Mapping[str, Any],
) -> None:
    expected = [
        f"### {item['rank']}. {item['headline']}" for item in top.get("items", [])
    ]
    actual = [line for line in lines if line.startswith("### ")]
    if actual != expected:
        raise GroundedBriefValidationError("Top item count, order, or headline changed")
    heading_indexes = [lines.index(heading) for heading in actual]
    regime_index = lines.index("## Market Regime")
    for item, start in zip(top.get("items", []), heading_indexes):
        later = [value for value in heading_indexes if value > start]
        end = min(later, default=regime_index)
        block_refs = set().union(
            *(citations.get(index, set()) for index in range(start + 1, end))
        )
        item_id = str(item["item_id"])
        support = _support_refs(item)
        if item_id not in block_refs:
            raise GroundedBriefValidationError(f"Top block missing item citation: {item_id}")
        if support and not block_refs.intersection(support):
            raise GroundedBriefValidationError(f"Top block missing support citation: {item_id}")


def _validate_section_references(
    lines: Sequence[str],
    citations: Mapping[int, Set[str]],
    daily: Mapping[str, Any],
) -> None:
    sections = (
        ("## Market Regime", "## Cross-Asset Signals", [daily.get("market_regime")]),
        ("## Cross-Asset Signals", "## Risks & Next 48 Hours", daily.get("cross_asset_signals", [])),
        (
            "## Risks & Next 48 Hours",
            "## Data Quality",
            list(daily.get("upcoming_events", [])) + list(daily.get("observed_market_stress", [])),
        ),
        ("## Data Quality", None, daily.get("data_quality_risks", [])),
    )
    daily_run = str(daily["run_id"])
    for start_heading, end_heading, objects in sections:
        start = lines.index(start_heading) + 1
        end = lines.index(end_heading) if end_heading else len(lines)
        section_refs = set().union(
            *(citations.get(index, set()) for index in range(start, end))
        )
        expected: Set[str] = set()
        for obj in objects:
            if isinstance(obj, Mapping):
                expected.update(_object_refs(obj))
        if not expected:
            expected.add(daily_run)
        if not section_refs.intersection(expected):
            raise GroundedBriefValidationError(
                f"section does not preserve references: {start_heading}"
            )


def _validate_assets(markdown: str, allowed_assets: Set[str]) -> None:
    text = CITATION_PATTERN.sub("", markdown)
    for token in ASSET_PATTERN.findall(text):
        if token in ALLOWED_UPPERCASE_WORDS or token in allowed_assets:
            continue
        if len(token) >= 2:
            raise GroundedBriefValidationError(f"asset-like symbol is not grounded: {token}")


def _validate_events(
    lines: Sequence[str],
    citations: Mapping[int, Set[str]],
    event_records: Mapping[str, str],
) -> None:
    known_names = tuple(event_records.values())
    for index, line in enumerate(lines):
        if line.startswith("#"):
            continue
        event_ids = citations.get(index, set()).intersection(event_records)
        named = [name for name in known_names if name and name in line]
        if named and not event_ids:
            raise GroundedBriefValidationError("event name is missing its event citation")
        if EVENT_CUE_PATTERN.search(line) and not named:
            raise GroundedBriefValidationError("event mention is not present in canonical input")


def _validate_numbers(lines: Sequence[str], allowed_numbers: Set[str]) -> None:
    for line in lines:
        if line.startswith("#") or line.startswith("Source / Evidence:"):
            continue
        without_refs = CITATION_PATTERN.sub("", line)
        unknown = set(NUMBER_PATTERN.findall(without_refs)) - allowed_numbers
        if unknown:
            raise GroundedBriefValidationError(
                f"numerical value is not grounded: {', '.join(sorted(unknown))}"
            )


def _parse_refs(value: str) -> Set[str]:
    return {item.strip().strip("`") for item in value.split(",") if item.strip()}


def _support_refs(item: Mapping[str, Any]) -> Set[str]:
    refs = set(str(value) for value in item.get("source_refs", []))
    for values in item.get("evidence_refs", {}).values():
        if isinstance(values, list):
            refs.update(str(value) for value in values)
    refs.add(str(item.get("source_object_id")))
    refs.discard("")
    refs.discard("None")
    return refs


def _object_refs(obj: Mapping[str, Any]) -> Set[str]:
    refs = {str(obj.get("object_id")), str(obj.get("source_run_id"))}
    for values in obj.get("evidence_refs", {}).values():
        if isinstance(values, list):
            refs.update(str(value) for value in values)
    refs.discard("None")
    refs.discard("")
    return refs
