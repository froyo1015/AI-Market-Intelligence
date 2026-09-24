"""Validate the two new public sidecars before Pages packaging."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .checkpoint import validate_morning_sidecar
from .model import project, validate


def validate_files(daily: Path, morning: Path) -> dict:
    found = {}
    if daily.is_file():
        payload = json.loads(daily.read_text())
        validate(payload, public=True)
        if payload != project(payload):
            raise ValueError("public reference projection mismatch")
        found["daily_reference"] = payload["status"]
    if morning.is_file():
        payload = json.loads(morning.read_text())
        validate_morning_sidecar(payload)
        found["morning_reference"] = payload["status"]
    return found


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--daily", type=Path, default=Path("docs/data/daily_market_reference_public.json"))
    parser.add_argument("--morning", type=Path, default=Path("docs/data/morning_daily_reference_public.json"))
    args = parser.parse_args()
    print(json.dumps(validate_files(args.daily, args.morning), sort_keys=True))


if __name__ == "__main__":
    main()
