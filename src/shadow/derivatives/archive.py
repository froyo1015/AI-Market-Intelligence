"""Private immutable replay archive; no collection or production integration."""

import argparse
import os
import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

from src.intelligence.daily_context import build_daily_context
from src.intelligence.evidence_boundary import read, check_output_path, write_context
from .consolidation import compose
from .production_validator import milliseconds
from .validator import digest, require
from .readiness import assess


def build_entry(request):
    require(set(request) == {"funding", "oi", "daily", "upstream", "cutoff", "archived_at"}, "archive request fields")
    require(milliseconds(request["archived_at"]) >= milliseconds(request["cutoff"]), "archive time precedes cutoff")
    require(isinstance(request["upstream"], list) and len(request["upstream"]) == 4, "upstream contract")
    b = compose(request["funding"], request["oi"], request["cutoff"])
    c = build_daily_context(request["daily"], *request["upstream"], b,
                           request["funding"], request["oi"], request["cutoff"])
    body = {"schema_contract": "derivatives_archive_entry_v1", "request": request,
            "bundle": b, "context": c}
    # JSON roundtrip also ensures callers cannot mutate the returned archive by alias.
    return json.loads(json.dumps({**body, "entry_hash": digest(body)}, allow_nan=False))


def replay(entry):
    require(entry == build_entry(entry["request"]), "archive replay mismatch")
    return {"bundle": entry["bundle"], "context": entry["context"]}


def append(root, request):
    entry = build_entry(request)
    target = check_output_path(Path(root) / request["cutoff"][:10] / (entry["entry_hash"][7:] + ".json"))
    target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    if target.exists():
        require(read(target) == entry, "archive collision")
        return target
    fd, pending = tempfile.mkstemp(prefix=".pending-", dir=target.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(entry, stream, sort_keys=True, indent=2, allow_nan=False)
            stream.flush()
            os.fsync(stream.fileno())
        try:
            os.link(pending, target)  # atomic, does not overwrite an existing entry
        except FileExistsError:
            require(read(target) == entry, "archive collision")
    finally:
        os.unlink(pending)  # only this call's private temporary file
    return target


def history(root, as_of, retention_days=30):
    cutoff = milliseconds(as_of)
    require(type(retention_days) is int and retention_days >= 7, "retention below readiness window")
    root = check_output_path(Path(root))
    day = datetime.strptime(as_of[:10], "%Y-%m-%d")
    dates = {(day - timedelta(days=n)).strftime("%Y-%m-%d") for n in range(retention_days)}
    samples, observed = [], set()
    cold = future = 0
    for path in sorted(root.glob("*/*.json")):
        check_output_path(path)
        entry = read(path)
        sample = replay(entry)
        req = entry["request"]
        require(path.name == entry["entry_hash"][7:] + ".json" and path.parent.name == req["cutoff"][:10], "archive path mismatch")
        if milliseconds(req["archived_at"]) > cutoff:
            future += 1
        elif req["cutoff"][:10] not in dates:
            cold += 1
        else:
            samples.append(sample)
            observed.add(req["cutoff"][:10])
    return samples, {"retention_days": retention_days, "active_entries": len(samples),
                     "cold_entries": cold, "not_yet_archived_entries": future,
                     "missing_dates": sorted(dates - observed), "deletion_enabled": False}


def readiness(root, as_of, retention_days=30):
    samples, inventory = history(root, as_of, retention_days)
    return {**assess(samples, as_of), "archive_inventory": inventory}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    add = commands.add_parser("append")
    add.add_argument("--input", required=True)
    add.add_argument("--archive", required=True)
    gate = commands.add_parser("readiness")
    gate.add_argument("--archive", required=True)
    gate.add_argument("--as-of", required=True)
    gate.add_argument("--output", required=True)
    args = parser.parse_args()
    if args.command == "append":
        append(args.archive, read(args.input))
    else:
        write_context(readiness(args.archive, args.as_of), args.output)


if __name__ == "__main__":
    main()
