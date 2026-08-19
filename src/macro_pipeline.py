"""Build a failure-isolated daily macro market proxy snapshot."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable, Optional, Sequence

import pandas as pd

from src.data.macro_adapter import (
    DEFAULT_MACRO_INSTRUMENTS,
    MacroDataAdapter,
    MacroDataError,
    MacroInstrument,
    YahooFinanceMacroAdapter,
)
from src.evidence.schema import confidence_label
from src.models.macro_schema import MacroSnapshot, MacroSnapshotRecord


DEFAULT_OUTPUT_PATH = Path(__file__).resolve().parent / "output" / "macro_snapshot.json"


def build_macro_snapshot(
    adapter: Optional[MacroDataAdapter] = None,
    instruments: Iterable[MacroInstrument] = DEFAULT_MACRO_INSTRUMENTS,
    period: str = "3mo",
    now: Optional[datetime] = None,
) -> MacroSnapshot:
    """Fetch each proxy independently so one provider error stays partial."""
    provider = adapter or YahooFinanceMacroAdapter()
    generated_at = _as_utc(now or datetime.now(timezone.utc))
    records = []

    for instrument in instruments:
        try:
            history = provider.fetch_history(instrument, period)
            closes, timestamp, status = _normalize_history(
                history,
                instrument,
                generated_at,
            )
            value = float(closes.iloc[-1])
            daily_change = _change(instrument, value, float(closes.iloc[-2]))
            weekly_change = (
                _change(instrument, value, float(closes.iloc[-6]))
                if len(closes) >= 6
                else None
            )
            score = (
                instrument.source_confidence
                if status == "success"
                else min(instrument.source_confidence, 0.50)
            )
            records.append(
                MacroSnapshotRecord(
                    symbol=instrument.symbol,
                    provider_symbol=instrument.provider_symbol,
                    name=instrument.name,
                    metric=instrument.metric,
                    value=_rounded(value, 6),
                    value_unit=instrument.value_unit,
                    daily_change=_rounded(daily_change, 4),
                    weekly_change=_rounded(weekly_change, 4),
                    change_metric=instrument.change_metric,
                    change_unit=instrument.change_unit,
                    timestamp=timestamp,
                    source=provider.source_name,
                    source_url=instrument.provider_url,
                    semantic_reference_url=instrument.semantic_reference_url,
                    status=status,
                    price_basis=instrument.price_basis,
                    asset_mapping=list(instrument.asset_mapping),
                    confidence_score=score,
                    confidence_label=confidence_label(score).value,
                )
            )
        except Exception as exc:
            records.append(
                MacroSnapshotRecord(
                    symbol=instrument.symbol,
                    provider_symbol=instrument.provider_symbol,
                    name=instrument.name,
                    metric=instrument.metric,
                    value=None,
                    value_unit=instrument.value_unit,
                    daily_change=None,
                    weekly_change=None,
                    change_metric=instrument.change_metric,
                    change_unit=instrument.change_unit,
                    timestamp=generated_at,
                    source=provider.source_name,
                    source_url=instrument.provider_url,
                    semantic_reference_url=instrument.semantic_reference_url,
                    status="failed",
                    price_basis=instrument.price_basis,
                    asset_mapping=list(instrument.asset_mapping),
                    confidence_score=0.0,
                    confidence_label="insufficient",
                    error=_safe_error(exc),
                )
            )

    return MacroSnapshot(
        generated_at=generated_at,
        source=provider.source_name,
        records=records,
    )


def write_macro_snapshot(
    snapshot: MacroSnapshot,
    output_path: Path = DEFAULT_OUTPUT_PATH,
) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = output_path.with_suffix(f"{output_path.suffix}.tmp")
    temporary_path.write_text(
        json.dumps(snapshot.to_dict(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary_path.replace(output_path)
    return output_path


def run_macro_pipeline(
    output_path: Path = DEFAULT_OUTPUT_PATH,
    period: str = "3mo",
) -> MacroSnapshot:
    snapshot = build_macro_snapshot(period=period)
    write_macro_snapshot(snapshot, output_path)
    return snapshot


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate the Phase 6.2-A macro market proxy snapshot."
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    parser.add_argument("--period", default="3mo")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    snapshot = run_macro_pipeline(output_path=args.output, period=args.period)
    payload = snapshot.to_dict()
    counts = {
        status: sum(record.status == status for record in snapshot.records)
        for status in ("success", "stale", "failed")
    }
    print(f"Wrote {len(snapshot.records)} macro records to {args.output}")
    print(
        "Status: "
        f"success={counts['success']} stale={counts['stale']} "
        f"failed={counts['failed']}"
    )
    return 1 if payload["status"] == "failed" else 0


def cli() -> None:
    raise SystemExit(main())


def _normalize_history(
    history: pd.DataFrame,
    instrument: MacroInstrument,
    now: datetime,
) -> tuple[pd.Series, datetime, str]:
    if "Close" not in history.columns:
        raise MacroDataError(
            f"provider response has no Close column for {instrument.symbol}"
        )
    closes = pd.to_numeric(history["Close"], errors="coerce").dropna()
    closes = closes[~closes.index.duplicated(keep="last")].sort_index()
    if len(closes) < 2:
        raise MacroDataError(
            f"not enough valid close values for {instrument.symbol}"
        )
    index = pd.DatetimeIndex(closes.index)
    if index.tz is None:
        index = index.tz_localize(timezone.utc)
    else:
        index = index.tz_convert(timezone.utc)
    closes.index = index
    timestamp = index[-1].to_pydatetime()
    status = (
        "stale"
        if now - timestamp > timedelta(days=instrument.stale_after_days)
        else "success"
    )
    return closes.astype(float), timestamp, status


def _change(instrument: MacroInstrument, latest: float, previous: float) -> float:
    if instrument.change_unit == "basis_points":
        return (latest - previous) * 100
    if previous == 0:
        raise MacroDataError(
            f"cannot calculate percent change from zero for {instrument.symbol}"
        )
    return ((latest / previous) - 1) * 100


def _rounded(value: Optional[float], digits: int) -> Optional[float]:
    return None if value is None else round(value, digits)


def _safe_error(exc: Exception) -> str:
    message = " ".join(str(exc).split())
    return f"{type(exc).__name__}: {message}"[:300]


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


if __name__ == "__main__":
    cli()
