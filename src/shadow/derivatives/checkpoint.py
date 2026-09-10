"""Encrypted Actions checkpoint. Never uploads plaintext replay captures."""

import argparse
import json
import os
from pathlib import Path
import subprocess
import tempfile

from src.intelligence.evidence_boundary import check_output_path, read
from .archive import append, replay
from .production_validator import unique_pairs, reject_constant
from .validator import require


def secret():
    key = os.environ.get("DERIVATIVES_ARCHIVE_PASSPHRASE", "")
    require(len(key) >= 32 and "\n" not in key and "\r" not in key, "archive credential unavailable")
    return key


def crypt(source, target, decrypt=False):
    key = secret()
    env = {k: v for k, v in os.environ.items() if k not in
           ("DERIVATIVES_ARCHIVE_PASSPHRASE", "GH_TOKEN", "GITHUB_TOKEN")}
    with tempfile.TemporaryDirectory() as home:
        command = ["gpg", "--homedir", home, "--batch", "--no-tty", "--pinentry-mode", "loopback",
                   "--passphrase-fd", "0", "--output", str(target)]
        command += ["--decrypt", str(source)] if decrypt else ["--symmetric", "--cipher-algo", "AES256", str(source)]
        try:
            p = subprocess.run(command, input=(key + "\n").encode(), stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, env=env, timeout=120)
            require(p.returncode == 0, "checkpoint cryptography failed")
        except (OSError, subprocess.TimeoutExpired):
            raise ValueError("checkpoint cryptography unavailable") from None


def seal(root, output, reports=None):
    root, output = check_output_path(root), check_output_path(output)
    require(not output.exists(), "checkpoint already exists")
    entries = []
    for path in sorted(root.glob("*/*.json")):
        check_output_path(path)
        entry = read(path)
        replay(entry)
        entries.append(entry)
    diagnostics = {} if reports is None else {n: read(check_output_path(Path(reports) / n)) for n in
        ("derivatives_readiness.json", "observation_index.json", "shadow_run.json")}
    output.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    with tempfile.TemporaryDirectory() as temporary:
        source, encrypted = Path(temporary) / "checkpoint.json", Path(temporary) / "checkpoint.gpg"
        source.write_text(json.dumps({"schema_contract": "derivatives_checkpoint_v1", "entries": entries,
                                     "diagnostics": diagnostics}, allow_nan=False))
        source.chmod(0o600)
        crypt(source, encrypted)
        with output.open("xb") as stream:
            stream.write(encrypted.read_bytes())


def restore(source, root):
    source, root = check_output_path(source), check_output_path(root)
    with tempfile.TemporaryDirectory() as temporary:
        target = Path(temporary) / "checkpoint.json"
        crypt(source, target, decrypt=True)
        payload = json.loads(target.read_text(), object_pairs_hook=unique_pairs, parse_constant=reject_constant)
        require(set(payload) == {"schema_contract", "entries", "diagnostics"}
                and payload["schema_contract"] == "derivatives_checkpoint_v1"
                and isinstance(payload["entries"], list), "invalid checkpoint")
        # Validate everything before the first append; partial restore cannot hide corruption.
        for entry in payload["entries"]:
            replay(entry)
        for entry in payload["entries"]:
            append(root, entry["request"])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("seal", "restore", "check-secret"))
    parser.add_argument("--archive")
    parser.add_argument("--file")
    parser.add_argument("--reports")
    args = parser.parse_args()
    if args.command == "check-secret":
        secret()
    elif args.command == "seal":
        seal(Path(args.archive), Path(args.file), args.reports)
    else:
        restore(Path(args.file), Path(args.archive))


if __name__ == "__main__":
    main()
