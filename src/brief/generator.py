"""Generate a deterministic Markdown brief from market_snapshot.json."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Sequence

from src.brief.templates import BRIEF_SECTIONS, render_instrument


OUTPUT_DIRECTORY = Path(__file__).resolve().parents[1] / "output"
DEFAULT_INPUT_PATH = OUTPUT_DIRECTORY / "market_snapshot.json"
DEFAULT_OUTPUT_PATH = OUTPUT_DIRECTORY / "daily_brief.md"


class BriefGenerationError(ValueError):
    """Raised when the input snapshot does not satisfy the minimal contract."""


def load_snapshot(input_path: Path) -> Dict[str, Any]:
    try:
        payload = json.loads(input_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise BriefGenerationError(f"snapshot not found: {input_path}") from exc
    except json.JSONDecodeError as exc:
        raise BriefGenerationError(f"snapshot is not valid JSON: {exc}") from exc

    if not isinstance(payload, dict):
        raise BriefGenerationError("snapshot root must be a JSON object")
    if not isinstance(payload.get("records"), list):
        raise BriefGenerationError("snapshot must contain a records array")
    return payload


def generate_brief(snapshot: Mapping[str, Any]) -> str:
    """Return Markdown using only snapshot values and deterministic rules."""
    raw_records = snapshot.get("records")
    if not isinstance(raw_records, list):
        raise BriefGenerationError("snapshot must contain a records array")

    records = _index_records(raw_records)
    selected_symbols = [
        source_symbol
        for _, instruments in BRIEF_SECTIONS
        for _, source_symbol in instruments
    ]
    selected_records = [
        records.get(symbol, _missing_record(symbol))
        for symbol in selected_symbols
    ]

    lines = [
        "# AI Market Brief",
        "",
        f"日期: {_report_date(snapshot.get('generated_at'))}",
        "",
        "## Market Overview",
        "",
        *_overview_lines(selected_records, str(snapshot.get("source", "N/A"))),
        "",
    ]

    for section, instruments in BRIEF_SECTIONS:
        lines.extend((f"## {section}", ""))
        for display_symbol, source_symbol in instruments:
            record = records.get(source_symbol, _missing_record(source_symbol))
            lines.extend((render_instrument(display_symbol, record), ""))

    return "\n".join(lines).rstrip() + "\n"


def write_brief(markdown: str, output_path: Path = DEFAULT_OUTPUT_PATH) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = output_path.with_suffix(f"{output_path.suffix}.tmp")
    temporary_path.write_text(markdown, encoding="utf-8")
    temporary_path.replace(output_path)
    return output_path


def run_generator(
    input_path: Path = DEFAULT_INPUT_PATH,
    output_path: Path = DEFAULT_OUTPUT_PATH,
) -> str:
    snapshot = load_snapshot(input_path)
    markdown = generate_brief(snapshot)
    write_brief(markdown, output_path)
    return markdown


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate a deterministic Daily Market Brief."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT_PATH,
        help=f"Input snapshot JSON (default: {DEFAULT_INPUT_PATH})",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help=f"Output Markdown path (default: {DEFAULT_OUTPUT_PATH})",
    )
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    markdown = run_generator(args.input, args.output)
    print(f"Wrote {len(markdown.splitlines())} lines to {args.output}")
    return 0


def cli() -> None:
    raise SystemExit(main())


def _index_records(records: Sequence[Any]) -> Dict[str, Mapping[str, Any]]:
    indexed: Dict[str, Mapping[str, Any]] = {}
    for record in records:
        if not isinstance(record, dict):
            continue
        symbol = record.get("symbol")
        if isinstance(symbol, str) and symbol not in indexed:
            indexed[symbol] = record
    return indexed


def _missing_record(symbol: str) -> Dict[str, Any]:
    return {
        "symbol": symbol,
        "status": "failed",
        "trend": "unavailable",
        "timestamp": "N/A",
        "source": "N/A",
    }


def _report_date(value: Any) -> str:
    if isinstance(value, str) and len(value) >= 10:
        return value[:10]
    return "N/A"


def _overview_lines(
    records: Sequence[Mapping[str, Any]],
    source: str,
) -> Sequence[str]:
    statuses = {
        status: sum(record.get("status") == status for record in records)
        for status in ("success", "stale", "failed")
    }
    daily_values = [
        value
        for record in records
        for value in [_number(record.get("daily_change"))]
        if value is not None
    ]
    positive = sum(value > 0 for value in daily_values)
    negative = sum(value < 0 for value in daily_values)
    flat_or_unavailable = len(records) - positive - negative

    return (
        f"- Instruments: {len(records)}",
        (
            "- Data status: "
            f"{statuses['success']} success, "
            f"{statuses['stale']} stale, "
            f"{statuses['failed']} failed"
        ),
        (
            "- Daily breadth: "
            f"{positive} positive, "
            f"{negative} negative, "
            f"{flat_or_unavailable} flat/unavailable"
        ),
        f"- Source: {source}",
    )


def _number(value: Any) -> Optional[float]:
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


if __name__ == "__main__":
    cli()

