"""Create-only public-safe capture and Morning sidecar checkpoints."""
from __future__ import annotations

import base64
import hashlib
import json
import os
import re
from dataclasses import dataclass
from datetime import date, datetime, time, timezone
from pathlib import Path
from urllib.parse import quote
from zoneinfo import ZoneInfo

from src.morning_report.baseline import validate_public as validate_morning
from src.morning_report.checkpoint import CheckpointError, GitHubTransport

from .model import (CAPTURE_VERSION, MORNING_VERSION, canonical_bytes, digest,
                    project, utc, validate)

ARCHIVE_BRANCH = "morning-reports"
MORNING_WORKFLOW = ".github/workflows/daily_market_brief.yml"
CAPTURE_WORKFLOW = ".github/workflows/daily_reference_capture.yml"
MAX_BYTES = 96_000
ZONE = ZoneInfo("Asia/Taipei")


def cutoff_for(day: str) -> datetime:
    try:
        parsed = date.fromisoformat(day)
    except ValueError:
        raise CheckpointError("invalid_report_date") from None
    if parsed.isoformat() != day:
        raise CheckpointError("invalid_report_date")
    return datetime.combine(parsed, time(8, 30), ZONE).astimezone(timezone.utc)


def validate_capture(payload: dict) -> None:
    if not isinstance(payload, dict) or set(payload) != {
        "version", "report_date", "timezone", "captured_at", "reference_sha256", "reference"
    } or payload["version"] != CAPTURE_VERSION or payload["timezone"] != "Asia/Taipei":
        raise ValueError("invalid capture contract")
    cutoff = cutoff_for(payload["report_date"])
    captured = utc(payload["captured_at"])
    if captured > cutoff or captured.astimezone(ZONE).date().isoformat() != payload["report_date"]:
        raise ValueError("capture outside Morning cutoff")
    validate(payload["reference"], public=True)
    if payload["reference"]["status"] == "unavailable":
        raise ValueError("empty capture cannot become baseline")
    if utc(payload["reference"]["generated_at"]) > captured or digest(payload["reference"]) != payload["reference_sha256"]:
        raise ValueError("capture source integrity failed")


def build_capture(reference: dict, *, captured_at: str) -> dict:
    public = project(reference)
    captured = utc(captured_at)
    payload = dict(version=CAPTURE_VERSION, report_date=captured.astimezone(ZONE).date().isoformat(),
                   timezone="Asia/Taipei", captured_at=captured_at,
                   reference_sha256=digest(public), reference=public)
    validate_capture(payload)
    return payload


def validate_morning_sidecar(payload: dict) -> None:
    if not isinstance(payload, dict) or set(payload) != {
        "version", "report_date", "timezone", "morning_report_id", "morning_report_sha256",
        "capture_sha256", "captured_at", "status", "reference"
    } or payload["version"] != MORNING_VERSION or payload["timezone"] != "Asia/Taipei":
        raise ValueError("invalid Morning reference sidecar")
    cutoff = cutoff_for(payload["report_date"])
    if not isinstance(payload["morning_report_id"], str) or not payload["morning_report_id"].startswith("morning_" + payload["report_date"] + "_"):
        raise ValueError("Morning identity invalid")
    for key in ("morning_report_sha256", "capture_sha256"):
        if not re.fullmatch(r"[0-9a-f]{64}", payload[key]):
            raise ValueError("sidecar digest missing")
    if utc(payload["captured_at"]) > cutoff:
        raise ValueError("late Morning reference")
    if utc(payload["captured_at"]).astimezone(ZONE).date().isoformat() != payload["report_date"]:
        raise ValueError("Morning capture date invalid")
    validate(payload["reference"], public=True)
    if utc(payload["reference"]["generated_at"]) > utc(payload["captured_at"]):
        raise ValueError("reference after Morning capture")
    if payload["reference"]["status"] == "unavailable" or payload["status"] != payload["reference"]["status"]:
        raise ValueError("Morning reference state invalid")


def build_morning_sidecar(capture: dict, morning: dict) -> dict:
    validate_capture(capture)
    validate_morning(morning)
    if capture["report_date"] != morning["baseline_for_date"]:
        raise ValueError("Morning/capture date mismatch")
    if utc(capture["captured_at"]) > utc(morning["baseline_timestamp"]):
        raise ValueError("future capture relative to Morning cutoff")
    payload = dict(version=MORNING_VERSION, report_date=capture["report_date"],
                   timezone="Asia/Taipei", morning_report_id=morning["report_id"],
                   morning_report_sha256=digest(morning), capture_sha256=digest(capture),
                   captured_at=capture["captured_at"], status=capture["reference"]["status"],
                   reference=capture["reference"])
    validate_morning_sidecar(payload)
    return payload


@dataclass(frozen=True)
class Stored:
    payload: dict
    created: bool
    creator_run_id: int


class ReferenceCheckpointStore:
    """Verified create-only checkpoint on the existing public Morning branch."""

    def __init__(self, transport: GitHubTransport, repo: str, *, branch: str = "main"):
        if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo) or branch != "main":
            raise CheckpointError("invalid_repository_identity")
        self.transport = transport
        self.repo = repo
        self.branch = branch
        self.base = "/repos/" + quote(repo, safe="/")

    @staticmethod
    def _kind(kind: str):
        if kind == "capture":
            return "daily_reference_capture_public.json", CAPTURE_WORKFLOW, validate_capture
        if kind == "morning":
            return "morning_daily_reference_public.json", MORNING_WORKFLOW, validate_morning_sidecar
        raise CheckpointError("invalid_checkpoint_kind")

    @classmethod
    def dated_path(cls, kind: str, day: str) -> str:
        cutoff_for(day)
        filename, _, _ = cls._kind(kind)
        return f"{day[:4]}/{day}/{filename}"

    def _request(self, method: str, path: str, body=None):
        status, result = self.transport.request(method, self.base + path, body)
        if status not in {200, 201, 404, 409, 422}:
            raise CheckpointError("github_api_unavailable")
        return status, result

    def _creator_run(self, kind: str, run_id: int, head_sha: str):
        _, workflow, _ = self._kind(kind)
        status, run = self._request("GET", f"/actions/runs/{run_id}")
        if status != 200 or not isinstance(run, dict) or (
            run.get("path") != workflow or run.get("head_branch") != self.branch or
            run.get("head_sha") != head_sha or
            (run.get("head_repository") or {}).get("full_name") != self.repo or
            (run.get("repository") or {}).get("full_name") != self.repo
        ):
            raise CheckpointError("creator_run_identity_mismatch")

    def _message(self, kind: str, day: str, run_id: int, head_sha: str, sha: str) -> str:
        _, workflow, _ = self._kind(kind)
        return "|".join(("daily-reference-checkpoint:v1", kind, day, self.repo,
                         self.branch, workflow, str(run_id), head_sha, sha))

    def discover(self, kind: str, day: str) -> Stored | None:
        path = self.dated_path(kind, day)
        _, _, validator = self._kind(kind)
        status, branch = self._request("GET", "/git/ref/heads/" + quote(ARCHIVE_BRANCH, safe=""))
        if status != 200 or not isinstance(branch, dict) or branch.get("ref") != "refs/heads/" + ARCHIVE_BRANCH:
            raise CheckpointError("archive_branch_missing")
        status, record = self._request("GET", "/contents/" + path + "?ref=" + ARCHIVE_BRANCH)
        if status == 404:
            history_status, history = self._request("GET", "/commits?sha=" + ARCHIVE_BRANCH +
                                                    "&path=" + quote(path, safe="") + "&per_page=2")
            if history_status != 200 or not isinstance(history, list):
                raise CheckpointError("checkpoint_history_unavailable")
            if history:
                raise CheckpointError("checkpoint_removed_from_archive")
            return None
        if status != 200 or not isinstance(record, dict) or record.get("path") != path or record.get("type") != "file" or record.get("encoding") != "base64":
            raise CheckpointError("checkpoint_invalid")
        try:
            raw = base64.b64decode("".join(record["content"].split()), validate=True)
            if not raw or len(raw) > MAX_BYTES:
                raise ValueError("size")
            payload = json.loads(raw)
            validator(payload)
            if payload["report_date"] != day or raw != canonical_bytes(payload):
                raise ValueError("identity")
        except (ValueError, TypeError, KeyError, AttributeError):
            raise CheckpointError("checkpoint_corrupt") from None
        sha = hashlib.sha256(raw).hexdigest()
        status, commits = self._request("GET", "/commits?sha=" + ARCHIVE_BRANCH +
                                        "&path=" + quote(path, safe="") + "&per_page=2")
        if status != 200 or not isinstance(commits, list) or len(commits) != 1:
            raise CheckpointError("checkpoint_history_modified")
        message = commits[0].get("commit", {}).get("message", "")
        pieces = message.split("|")
        if len(pieces) != 9 or not pieces[6].isdigit():
            raise CheckpointError("checkpoint_provenance_invalid")
        run_id = int(pieces[6])
        if message != self._message(kind, day, run_id, pieces[7], sha):
            raise CheckpointError("checkpoint_provenance_invalid")
        self._creator_run(kind, run_id, pieces[7])
        return Stored(payload, False, run_id)

    def create_or_get(self, kind: str, candidate: dict, *, run_id: int, head_sha: str) -> Stored:
        _, _, validator = self._kind(kind)
        validator(candidate)
        day = candidate["report_date"]
        existing = self.discover(kind, day)
        if existing is not None:
            return existing
        self._creator_run(kind, run_id, head_sha)
        raw = canonical_bytes(candidate)
        if len(raw) > MAX_BYTES:
            raise CheckpointError("checkpoint_too_large")
        body = dict(message=self._message(kind, day, run_id, head_sha,
                                          hashlib.sha256(raw).hexdigest()),
                    content=base64.b64encode(raw).decode(), branch=ARCHIVE_BRANCH)
        status, _ = self._request("PUT", "/contents/" + self.dated_path(kind, day), body)
        if status == 201:
            winner = self.discover(kind, day)
            if winner is None or winner.payload != candidate:
                raise CheckpointError("checkpoint_write_not_confirmed")
            return Stored(winner.payload, True, winner.creator_run_id)
        if status in {409, 422}:
            winner = self.discover(kind, day)
            if winner is not None:
                return winner
            raise CheckpointError("checkpoint_conflict_unresolved")
        raise CheckpointError("checkpoint_write_failed")


def store_from_environment() -> ReferenceCheckpointStore:
    if os.environ.get("GITHUB_REF_NAME") != "main":
        raise CheckpointError("wrong_source_branch")
    return ReferenceCheckpointStore(GitHubTransport(os.environ.get("GITHUB_TOKEN")),
                                    os.environ.get("GITHUB_REPOSITORY", ""))


def run_capture(store: ReferenceCheckpointStore, *, now: datetime | None = None, fetcher=None,
                public_path: Path, run_id: int, head_sha: str) -> Stored:
    from .pipeline import collect
    from .sources import fetch
    started = now or datetime.now(timezone.utc)
    day = started.astimezone(ZONE).date().isoformat()
    existing = store.discover("capture", day)
    if existing is not None:
        result = existing
    else:
        if started.astimezone(ZONE).time() < time(8, 0):
            raise CheckpointError("capture_window_not_open")
        if started.astimezone(timezone.utc) > cutoff_for(day):
            raise CheckpointError("capture_after_cutoff")
        reference = collect(now=now, fetcher=fetcher or fetch)
        completed = now or datetime.now(timezone.utc)
        if completed.astimezone(timezone.utc) > cutoff_for(day):
            raise CheckpointError("capture_after_cutoff")
        candidate = build_capture(reference, captured_at=completed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"))
        result = store.create_or_get("capture", candidate, run_id=run_id, head_sha=head_sha)
    public_path.parent.mkdir(parents=True, exist_ok=True)
    public_path.write_bytes(canonical_bytes(result.payload))
    return result


def run_morning(store: ReferenceCheckpointStore, morning: dict, public_path: Path,
                *, run_id: int, head_sha: str) -> Stored | None:
    validate_morning(morning)
    day = morning["baseline_for_date"]
    existing = store.discover("morning", day)
    if existing is not None:
        if existing.payload["morning_report_id"] != morning["report_id"] or existing.payload["morning_report_sha256"] != digest(morning):
            raise CheckpointError("morning_sidecar_identity_mismatch")
        captured = store.discover("capture", day)
        if captured is None or existing.payload["capture_sha256"] != digest(captured.payload):
            raise CheckpointError("morning_capture_provenance_missing")
        result = existing
    else:
        captured = store.discover("capture", day)
        if captured is None:
            return None
        candidate = build_morning_sidecar(captured.payload, morning)
        result = store.create_or_get("morning", candidate, run_id=run_id, head_sha=head_sha)
        if result.payload["morning_report_id"] != morning["report_id"] or result.payload["capture_sha256"] != digest(captured.payload):
            raise CheckpointError("morning_sidecar_identity_mismatch")
    public_path.parent.mkdir(parents=True, exist_ok=True)
    public_path.write_bytes(canonical_bytes(result.payload))
    return result
