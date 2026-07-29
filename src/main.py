"""Command-line entry point for the Phase 1.1 snapshot pipeline."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Optional, Sequence

from src.models.schema import SnapshotStatus
from src.pipeline import DEFAULT_OUTPUT_PATH, run_pipeline


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate the AI Market Brief market snapshot JSON."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help=f"Output JSON path (default: {DEFAULT_OUTPUT_PATH})",
    )
    parser.add_argument(
        "--period",
        default="3mo",
        help="Yahoo Finance history period (default: 3mo)",
    )
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    snapshot = run_pipeline(output_path=args.output, period=args.period)

    counts = {
        status.value: sum(
            record.status is status for record in snapshot.records
        )
        for status in SnapshotStatus
    }
    print(f"Wrote {len(snapshot.records)} records to {args.output}")
    print(
        "Status: "
        f"success={counts['success']} "
        f"stale={counts['stale']} "
        f"failed={counts['failed']}"
    )
    return 1 if counts["failed"] == len(snapshot.records) else 0


def cli() -> None:
    raise SystemExit(main())


if __name__ == "__main__":
    cli()

