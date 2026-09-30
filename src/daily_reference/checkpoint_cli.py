"""Create or restore the pre-cutoff capture and its Morning Report sidecar."""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from src.morning_report.checkpoint import CheckpointError

from .checkpoint import ZONE, cutoff_for, run_capture, run_morning, store_from_environment


# Codes are literals, never provider messages or arbitrary exception text.
FAILURE_STAGES = {
    "missing_runtime_token": "configuration",
    "wrong_source_branch": "configuration",
    "invalid_repository_identity": "configuration",
    "capture_window_not_open": "capture_window",
    "capture_after_cutoff": "capture_window",
    "archive_branch_missing": "checkpoint_discovery",
    "checkpoint_history_unavailable": "checkpoint_discovery",
    "checkpoint_removed_from_archive": "checkpoint_discovery",
    "checkpoint_invalid": "checkpoint_validation",
    "checkpoint_corrupt": "checkpoint_validation",
    "checkpoint_history_modified": "checkpoint_validation",
    "checkpoint_provenance_invalid": "checkpoint_validation",
    "creator_run_identity_mismatch": "checkpoint_validation",
    "checkpoint_too_large": "checkpoint_persistence",
    "checkpoint_write_not_confirmed": "checkpoint_persistence",
    "checkpoint_conflict_unresolved": "checkpoint_persistence",
    "checkpoint_write_failed": "checkpoint_persistence",
    # This code can arise during discovery or persistence; do not claim either.
    "github_api_unavailable": "checkpoint_io",
    "morning_sidecar_identity_mismatch": "morning_binding",
    "morning_capture_provenance_missing": "morning_binding",
}


def _log_failure(error: Exception, stage: str, configured_cutoff: datetime) -> None:
    if isinstance(error, CheckpointError):
        reason = error.reason if isinstance(error.reason, str) and error.reason in FAILURE_STAGES else "checkpoint_failure"
        stage = FAILURE_STAGES.get(reason, stage)
    elif isinstance(error, FileNotFoundError):
        reason = "required_file_missing"
    elif isinstance(error, KeyError):
        reason = "required_field_missing"
    elif isinstance(error, TypeError):
        reason = "invalid_data_type"
    else:
        reason = "validation_failed"
    print(json.dumps({
        "stage": stage,
        "reason_code": reason,
        "current_utc_timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "configured_cutoff": configured_cutoff.isoformat().replace("+00:00", "Z"),
    }, sort_keys=True), file=sys.stderr)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("capture", "morning"))
    parser.add_argument("--morning-report", type=Path, default=Path("docs/data/morning_report_public.json"))
    parser.add_argument("--public-out", type=Path)
    args = parser.parse_args()
    configured_cutoff = cutoff_for(datetime.now(timezone.utc).astimezone(ZONE).date().isoformat())
    stage = "configuration"
    try:
        store = store_from_environment()
        run_id = int(os.environ["GITHUB_RUN_ID"])
        head_sha = os.environ["GITHUB_SHA"]
        if args.mode == "capture":
            path = args.public_out or Path("work/daily-reference-capture/daily_reference_capture_public.json")
            stage = "capture_service"
            result = run_capture(store, public_path=path, run_id=run_id, head_sha=head_sha)
        else:
            path = args.public_out or Path("docs/data/morning_daily_reference_public.json")
            stage = "morning_report_read"
            path.unlink(missing_ok=True)
            morning = json.loads(args.morning_report.read_text())
            # A historical reuse belongs to its report date, not today's date.
            # Invalid metadata is still rejected by the existing service validator.
            if isinstance(morning, dict):
                try:
                    configured_cutoff = cutoff_for(morning.get("baseline_for_date"))
                except (CheckpointError, TypeError):
                    pass
            stage = "morning_binding"
            result = run_morning(store, morning, path, run_id=run_id, head_sha=head_sha)
            if result is None:
                print(json.dumps({"status": "unavailable", "reason": "no_pre_cutoff_capture"}))
                return
        stage = "result_reporting"
        print(json.dumps({"report_date": result.payload["report_date"],
                          "created": result.created, "creator_run_id": result.creator_run_id,
                          "status": result.payload.get("status", result.payload.get("reference", {}).get("status"))},
                         sort_keys=True))
    except (CheckpointError, ValueError, KeyError, FileNotFoundError, TypeError) as error:
        # Provider bodies, headers, tokens and local paths are never logged.
        _log_failure(error, stage, configured_cutoff)
        raise SystemExit("daily_reference_checkpoint_failed") from None


if __name__ == "__main__":
    main()
