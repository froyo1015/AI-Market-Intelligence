"""Create or restore the pre-cutoff capture and its Morning Report sidecar."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from src.morning_report.checkpoint import CheckpointError

from .checkpoint import run_capture, run_morning, store_from_environment


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("capture", "morning"))
    parser.add_argument("--morning-report", type=Path, default=Path("docs/data/morning_report_public.json"))
    parser.add_argument("--public-out", type=Path)
    args = parser.parse_args()
    try:
        store = store_from_environment()
        run_id = int(os.environ["GITHUB_RUN_ID"])
        head_sha = os.environ["GITHUB_SHA"]
        if args.mode == "capture":
            path = args.public_out or Path("work/daily-reference-capture/daily_reference_capture_public.json")
            result = run_capture(store, public_path=path, run_id=run_id, head_sha=head_sha)
        else:
            path = args.public_out or Path("docs/data/morning_daily_reference_public.json")
            path.unlink(missing_ok=True)
            morning = json.loads(args.morning_report.read_text())
            result = run_morning(store, morning, path, run_id=run_id, head_sha=head_sha)
            if result is None:
                print(json.dumps({"status": "unavailable", "reason": "no_pre_cutoff_capture"}))
                return
        print(json.dumps({"report_date": result.payload["report_date"],
                          "created": result.created, "creator_run_id": result.creator_run_id,
                          "status": result.payload.get("status", result.payload.get("reference", {}).get("status"))},
                         sort_keys=True))
    except (CheckpointError, ValueError, KeyError, FileNotFoundError, TypeError):
        # Provider bodies, headers, tokens and local paths are never logged.
        raise SystemExit("daily_reference_checkpoint_failed") from None


if __name__ == "__main__":
    main()
