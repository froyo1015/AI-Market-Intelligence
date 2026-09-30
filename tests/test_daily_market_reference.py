"""Official daily references, publication safety and immutable Morning capture."""
from __future__ import annotations

import base64
import copy
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from src.daily_reference.checkpoint import (
    ReferenceCheckpointStore, build_capture, build_morning_sidecar,
    run_capture, run_morning, validate_capture, validate_morning_sidecar,
)
from src.daily_reference.model import canonical_bytes, context_for, project, validate
from src.daily_reference.pipeline import collect, run
from src.daily_reference.public_validate import validate_files
from src.daily_reference.sources import ECB_URL, H15_URL, SourceError, parse_ecb, parse_h15
from src.morning_report.checkpoint import CheckpointError

NOW = datetime(2026, 9, 23, 0, 10, tzinfo=timezone.utc)
LATER = datetime(2026, 9, 23, 1, 10, tzinfo=timezone.utc)
REPO = "froyo1015/AI-Market-Intelligence"
SHA = "a" * 40
ECB = b"""<?xml version='1.0'?><Envelope><Cube><Cube time='2026-09-22'>
<Cube currency='USD' rate='1.2000'/><Cube currency='JPY' rate='180.00'/>
<Cube currency='GBP' rate='0.8000'/></Cube></Cube></Envelope>"""
H15 = b"""<html><div>Release date: September 22, 2026</div>
<table id='h15table'><thead><tr><th>Instruments</th><th>2026<br>Sep<br>18</th><th>2026<br>Sep<br>21</th></tr></thead>
<tbody><tr><th>Treasury constant maturities</th><td></td><td></td></tr>
<tr><th>Nominal <a>9</a></th><td></td><td></td></tr>
<tr><th>10-year</th><td>4.92</td><td>4.96</td></tr>
<tr><th>Inflation indexed <a>10</a></th><td></td><td></td></tr>
<tr><th>10-year</th><td>2.55</td><td>2.50</td></tr></tbody></table></html>"""


def feeds(url):
    return H15 if url == H15_URL else ECB if url == ECB_URL else None


def morning_candidate(day="2026-09-23"):
    # Existing public Morning contract fixture is independently validated.
    from src.morning_report.baseline import build, public_projection
    root = Path("src/output")
    daily_bytes = (root / "daily_intelligence.json").read_bytes()
    top_bytes = (root / "top_intelligence.json").read_bytes()
    # Use its original fixed date; baseline fixture and source artifact dates agree.
    return public_projection(build(json.loads(daily_bytes), json.loads(top_bytes),
                                   json.loads((root / "run_manifest.json").read_text()),
                                   daily_bytes, top_bytes, "2026-09-04T00:30:00Z",
                                   "2026-09-04T00:32:00Z"))


def test_normal_sources_units_cross_rates_and_public_projection(tmp_path):
    result = run(canonical_path=tmp_path / "daily_market_reference.json",
                 public_path=tmp_path / "daily_market_reference_public.json",
                 now=NOW, fetcher=feeds)
    assert result["status"] == "available"
    values = {a["asset_id"]: a["reference_value"] for a in result["assets"]}
    assert values == {"US10Y": "4.96", "EURUSD": "1.2", "USDJPY": "150", "GBPUSD": "1.5"}
    assert result["assets"][0]["reference_period"] == "2026-09-21"
    assert result["assets"][0]["release_date"] == "2026-09-22"
    assert result["assets"][0]["context_zh"] == "美國 10 年期國債收益率的官方每日參考值為 4.96%（資料日期 2026-09-21）。"
    assert result["assets"][2]["provenance"]["input_series"] == ["ecb_jpy_per_eur", "ecb_usd_per_eur"]
    assert validate_files(tmp_path / "daily_market_reference_public.json", tmp_path / "missing") == {"daily_reference": "available"}
    assert (tmp_path / "daily_market_reference_public.json").read_bytes() == canonical_bytes(project(result))


def test_stale_and_missing_sources_isolated():
    stale = collect(now=datetime(2026, 9, 29, 0, 10, tzinfo=timezone.utc), fetcher=feeds)
    assert stale["status"] == "partial" and all(a["status"] == "stale" for a in stale["assets"])
    def no_h15(url):
        if url == H15_URL:
            raise OSError("private transport detail")
        return ECB
    partial = collect(now=NOW, fetcher=no_h15)
    assert partial["status"] == "partial"
    assert partial["assets"][0]["reference_value"] is None
    assert partial["assets"][0]["message_zh"] == "資料暫不可用"
    assert partial["assets"][0]["context_zh"] == "資料暫不可用。"
    assert all(a["status"] == "available" for a in partial["assets"][1:])
    assert "private transport detail" not in canonical_bytes(partial).decode()
    unavailable = collect(now=NOW, fetcher=lambda _: (_ for _ in ()).throw(TimeoutError("private")))
    assert unavailable["status"] == "unavailable"
    assert all(a["reference_value"] is None for a in unavailable["assets"])


def test_failed_generation_clears_previous_public_projection(tmp_path, monkeypatch):
    canonical = tmp_path / "daily_market_reference.json"
    public = tmp_path / "daily_market_reference_public.json"
    canonical.write_text("old")
    public.write_text("old")
    def fail(**_):
        raise ValueError("invalid current run")
    monkeypatch.setattr("src.daily_reference.pipeline.collect", fail)
    with pytest.raises(ValueError):
        run(canonical_path=canonical, public_path=public, now=NOW, fetcher=feeds)
    assert not canonical.exists() and not public.exists()


def test_malformed_future_duplicate_and_wrong_h15_row():
    with pytest.raises(SourceError): parse_ecb(ECB.replace(b"2026-09-22", b"2026-09-24"), NOW)
    with pytest.raises(SourceError): parse_ecb(ECB.replace(b"<Cube currency='GBP'", b"<Cube currency='USD'"), NOW)
    with pytest.raises(SourceError): parse_ecb(ECB.replace(b"rate='1.2000'", b"rate='0'"), NOW)
    assert parse_h15(H15.replace(b"4.96", b"n.a."), NOW)["period"] == "2026-09-18"
    with pytest.raises(SourceError): parse_h15(H15.replace(b"4.96", b"n.a.").replace(b"4.92", b"n.a."), NOW)
    with pytest.raises(SourceError): parse_h15(H15.replace(b"Nominal", b"Not-Nominal"), NOW)
    with pytest.raises(SourceError): parse_h15(H15.replace(b"September 22", b"September 24"), NOW)
    with pytest.raises(SourceError): parse_ecb(b"<!DOCTYPE x><Envelope/>", NOW)


def test_timezones_date_precision_and_public_safety():
    result = collect(now=NOW, fetcher=feeds)
    assert all(a["timestamp_precision"] == "date" and len(a["source_timestamp"]) == 10
               for a in result["assets"])
    assert result["assets"][1]["timezone"] == "Europe/Berlin"
    unsafe = copy.deepcopy(result)
    unsafe["assets"][0]["provenance"]["raw_response"] = "secret"
    with pytest.raises(ValueError): validate(unsafe, public=True)
    unsafe = copy.deepcopy(result)
    unsafe["assets"][0]["reference_value"] = "NaN"
    with pytest.raises(ValueError): validate(unsafe)
    unsafe = copy.deepcopy(result)
    unsafe["assets"][2]["reference_value"] = "151"
    unsafe["assets"][2]["context_zh"] = context_for("USDJPY", "151", unsafe["assets"][2]["reference_period"])
    with pytest.raises(ValueError, match="cross-rate value mismatch"): validate(unsafe)
    unsafe = copy.deepcopy(result)
    unsafe["assets"][0]["freshness"]["age_seconds"] = 0
    with pytest.raises(ValueError, match="reference age mismatch"): validate(unsafe)


def test_ecb_dst_changes_age_without_inventing_source_time():
    spring = ECB.replace(b"2026-09-22", b"2026-03-30")
    autumn = ECB.replace(b"2026-09-22", b"2026-10-26")
    spring_now = datetime(2026, 3, 30, 23, tzinfo=timezone.utc)
    autumn_now = datetime(2026, 10, 26, 23, tzinfo=timezone.utc)
    spring_result = collect(now=spring_now, fetcher=lambda url: H15 if url == H15_URL else spring)
    autumn_result = collect(now=autumn_now, fetcher=lambda url: H15 if url == H15_URL else autumn)
    assert spring_result["assets"][1]["freshness"]["age_seconds"] == 25 * 3600
    assert autumn_result["assets"][1]["freshness"]["age_seconds"] == 24 * 3600
    assert spring_result["assets"][1]["source_timestamp"] == "2026-03-30"


class FakeGitHub:
    def __init__(self):
        self.files = {}
        self.messages = {}
        self.puts = 0
        self.run_workflow = None

    def request(self, method, path, body=None):
        if "/git/ref/heads/morning-reports" in path:
            return 200, {"ref": "refs/heads/morning-reports"}
        if "/actions/runs/" in path:
            workflow = (".github/workflows/daily_reference_capture.yml" if path.endswith("/801") else
                        ".github/workflows/daily_market_brief.yml")
            return 200, dict(path=self.run_workflow or workflow, head_branch="main", head_sha=SHA,
                             head_repository={"full_name": REPO}, repository={"full_name": REPO})
        if "/commits?" in path:
            key = path.split("path=", 1)[1].split("&", 1)[0].replace("%2F", "/")
            return 200, ([{"commit": {"message": self.messages[key]}}] if key in self.messages else [])
        if "/contents/" in path:
            key = path.split("/contents/", 1)[1].split("?", 1)[0]
            if method == "GET":
                if key not in self.files:
                    return 404, None
                return 200, dict(path=key, type="file", encoding="base64",
                                 content=base64.b64encode(self.files[key]).decode())
            self.puts += 1
            if key in self.files:
                return 422, None
            self.files[key] = base64.b64decode(body["content"])
            self.messages[key] = body["message"]
            return 201, {}
        raise AssertionError((method, path))


def test_pre_cutoff_capture_immutable_and_late_rejected(tmp_path):
    fake = FakeGitHub()
    store = ReferenceCheckpointStore(fake, REPO)
    first = run_capture(store, now=NOW, fetcher=feeds, public_path=tmp_path / "first.json",
                        run_id=801, head_sha=SHA)
    assert first.created and fake.puts == 1
    second = run_capture(store, now=LATER, fetcher=lambda _: (_ for _ in ()).throw(AssertionError()),
                         public_path=tmp_path / "second.json", run_id=900, head_sha=SHA)
    assert not second.created and second.payload == first.payload and fake.puts == 1
    assert (tmp_path / "first.json").read_bytes() == (tmp_path / "second.json").read_bytes()
    with pytest.raises(CheckpointError, match="capture_after_cutoff"):
        run_capture(ReferenceCheckpointStore(FakeGitHub(), REPO), now=LATER,
                    fetcher=feeds, public_path=tmp_path / "late.json", run_id=801, head_sha=SHA)
    with pytest.raises(CheckpointError, match="capture_window_not_open"):
        run_capture(ReferenceCheckpointStore(FakeGitHub(), REPO),
                    now=datetime(2026, 9, 22, 16, 5, tzinfo=timezone.utc),
                    fetcher=feeds, public_path=tmp_path / "early.json", run_id=801, head_sha=SHA)
    bad = copy.deepcopy(first.payload)
    bad["captured_at"] = "2026-09-23T00:40:00Z"
    with pytest.raises(ValueError): validate_capture(bad)
    next_day = datetime(2026, 9, 24, 0, 10, tzinfo=timezone.utc)
    rollover = run_capture(store, now=next_day, fetcher=feeds,
                           public_path=tmp_path / "next.json", run_id=801, head_sha=SHA)
    assert rollover.created and rollover.payload["report_date"] == "2026-09-24"
    assert first.payload["report_date"] == "2026-09-23" and fake.puts == 2


def test_morning_sidecar_binding_and_next_day_rollover(tmp_path):
    # Morning source fixture belongs to Sep 4; use Sep 4 official reference fixture.
    current = datetime(2026, 9, 4, 0, 10, tzinfo=timezone.utc)
    ecb = ECB.replace(b"2026-09-22", b"2026-09-03")
    h15 = H15.replace(b"2026-09-22", b"2026-09-03").replace(b"September 22", b"September 03").replace(b"Sep<br>18", b"Sep<br>01").replace(b"Sep<br>21", b"Sep<br>02")
    reference = collect(now=current, fetcher=lambda url: h15 if url == H15_URL else ecb)
    capture = build_capture(reference, captured_at="2026-09-04T00:10:00Z")
    morning = morning_candidate()
    sidecar = build_morning_sidecar(capture, morning)
    validate_morning_sidecar(sidecar)
    assert sidecar["morning_report_id"] == morning["report_id"]
    fake = FakeGitHub()
    store = ReferenceCheckpointStore(fake, REPO)
    store.create_or_get("capture", capture, run_id=801, head_sha=SHA)
    first = run_morning(store, morning, tmp_path / "morning.json", run_id=900, head_sha=SHA)
    assert first.created and fake.puts == 2
    again = run_morning(store, morning, tmp_path / "later.json", run_id=901, head_sha=SHA)
    assert not again.created and first.payload == again.payload and fake.puts == 2
    assert ReferenceCheckpointStore.dated_path("capture", "2026-09-05") != ReferenceCheckpointStore.dated_path("capture", "2026-09-04")
    assert (tmp_path / "morning.json").read_bytes() == (tmp_path / "later.json").read_bytes()
    missing = run_morning(ReferenceCheckpointStore(FakeGitHub(), REPO), morning,
                          tmp_path / "missing.json", run_id=900, head_sha=SHA)
    assert missing is None and not (tmp_path / "missing.json").exists()


def test_checkpoint_wrong_origin_and_corruption_fail_closed(tmp_path):
    fake = FakeGitHub()
    store = ReferenceCheckpointStore(fake, REPO)
    run_capture(store, now=NOW, fetcher=feeds, public_path=tmp_path / "capture.json",
                run_id=801, head_sha=SHA)
    fake.run_workflow = ".github/workflows/other.yml"
    with pytest.raises(CheckpointError, match="creator_run_identity_mismatch"):
        store.discover("capture", "2026-09-23")
    fake.run_workflow = None
    key = ReferenceCheckpointStore.dated_path("capture", "2026-09-23")
    fake.files[key] = b'{broken'
    with pytest.raises(CheckpointError, match="checkpoint_corrupt"):
        store.discover("capture", "2026-09-23")
    del fake.files[key]
    with pytest.raises(CheckpointError, match="checkpoint_removed_from_archive"):
        store.discover("capture", "2026-09-23")


def test_workflow_publication_and_isolation():
    capture = Path(".github/workflows/daily_reference_capture.yml").read_text()
    workflow = Path(".github/workflows/daily_market_brief.yml").read_text()
    assert 'cron: "3,13,23 0 * * *"' in capture
    assert "group: daily-reference-capture" in capture
    assert "cancel-in-progress: false" in capture
    assert "src.daily_reference.checkpoint_cli capture" in capture
    assert workflow.index("Regenerate intelligence pipeline") < workflow.index("Bind pre-cutoff daily reference")
    assert workflow.index("Generate official daily market reference") < workflow.index("Validate daily reference public sidecars")
    assert "src.daily_reference.checkpoint_cli morning" in workflow
    assert "docs/data/" in workflow
    assert "daily_reference" not in Path("src/intelligence/pipeline.py").read_text()


@pytest.mark.parametrize("first_success_minute", [3, 13, 23])
def test_staggered_schedules_create_once_then_reuse(tmp_path, first_success_minute):
    fake = FakeGitHub()
    fake.run_workflow = ".github/workflows/daily_reference_capture.yml"
    store = ReferenceCheckpointStore(fake, REPO)
    source_calls = []
    baseline_bytes = None
    creator = None
    for index, minute in enumerate((3, 13, 23)):
        now = datetime(2026, 9, 23, 0, minute, tzinfo=timezone.utc)
        def scheduled_fetch(url):
            source_calls.append((minute, url))
            if minute < first_success_minute:
                raise TimeoutError("provider unavailable")
            return feeds(url)
        path = tmp_path / f"run-{minute}.json"
        if minute < first_success_minute:
            with pytest.raises(ValueError, match="empty capture"):
                run_capture(store, now=now, fetcher=scheduled_fetch, public_path=path,
                            run_id=801 + index, head_sha=SHA)
            assert fake.puts == 0 and not path.exists()
            continue
        result = run_capture(store, now=now, fetcher=scheduled_fetch, public_path=path,
                             run_id=801 + index, head_sha=SHA)
        if baseline_bytes is None:
            assert result.created
            baseline_bytes = path.read_bytes()
            creator = result.creator_run_id
        else:
            assert not result.created and result.creator_run_id == creator
            assert path.read_bytes() == baseline_bytes
        assert fake.puts == 1 and len(fake.files) == 1
    assert [minute for minute, _ in source_calls].count(first_success_minute) == 2
    assert all(minute <= first_success_minute for minute, _ in source_calls)
    # A delayed schedule may restore the established baseline, never refresh it.
    def forbidden_fetch(_):
        raise AssertionError("delayed reuse must not fetch")
    late = run_capture(store, now=LATER, fetcher=forbidden_fetch,
                       public_path=tmp_path / "delayed.json", run_id=899, head_sha=SHA)
    assert not late.created and late.creator_run_id == creator
    assert (tmp_path / "delayed.json").read_bytes() == baseline_bytes and fake.puts == 1


def test_all_staggered_runs_delayed_fail_closed_without_source_calls(tmp_path):
    fake = FakeGitHub()
    store = ReferenceCheckpointStore(fake, REPO)
    def forbidden_fetch(_):
        raise AssertionError("post-cutoff creates must not fetch")
    for index in range(3):
        with pytest.raises(CheckpointError, match="capture_after_cutoff"):
            run_capture(store, now=LATER, fetcher=forbidden_fetch,
                        public_path=tmp_path / f"late-{index}.json", run_id=801 + index, head_sha=SHA)
    assert fake.puts == 0 and not fake.files and not list(tmp_path.iterdir())


@pytest.mark.parametrize("conflict_status", [409, 422])
def test_capture_competing_writer_preserves_winner(tmp_path, conflict_status):
    winner = build_capture(collect(now=NOW, fetcher=feeds), captured_at="2026-09-23T00:10:00Z")
    later = datetime(2026, 9, 23, 0, 13, tzinfo=timezone.utc)
    loser = build_capture(collect(now=later, fetcher=feeds), captured_at="2026-09-23T00:13:00Z")
    class CompetingGitHub(FakeGitHub):
        def request(self, method, path, body=None):
            if method == "PUT":
                assert "sha" not in body  # Create-only request cannot update an existing file.
                self.puts += 1
                key = ReferenceCheckpointStore.dated_path("capture", "2026-09-23")
                self.files[key] = canonical_bytes(winner)
                self.messages[key] = store._message("capture", "2026-09-23", 801, SHA,
                                                    hashlib.sha256(self.files[key]).hexdigest())
                return conflict_status, None
            return super().request(method, path, body)
    fake = CompetingGitHub()
    fake.run_workflow = ".github/workflows/daily_reference_capture.yml"
    store = ReferenceCheckpointStore(fake, REPO)
    result = store.create_or_get("capture", loser, run_id=802, head_sha=SHA)
    assert not result.created and result.creator_run_id == 801 and result.payload == winner
    assert list(fake.files.values()) == [canonical_bytes(winner)] and fake.puts == 1


def _capture_cli(monkeypatch, store, output, now):
    import src.daily_reference.checkpoint_cli as cli

    class FixedClock(datetime):
        @classmethod
        def now(cls, tz=None):
            return now.astimezone(tz) if tz else now.replace(tzinfo=None)

    monkeypatch.setattr(cli, "datetime", FixedClock)
    monkeypatch.setattr(cli, "store_from_environment", lambda: store)
    monkeypatch.setenv("GITHUB_RUN_ID", "801")
    monkeypatch.setenv("GITHUB_SHA", SHA)
    monkeypatch.setattr("sys.argv", ["checkpoint_cli", "capture", "--public-out", str(output)])
    return cli


def test_capture_cli_success_and_existing_checkpoint_reuse(monkeypatch, tmp_path, capsys):
    fake = FakeGitHub()
    store = ReferenceCheckpointStore(fake, REPO)
    output = tmp_path / "capture.json"
    cli = _capture_cli(monkeypatch, store, output, NOW)
    monkeypatch.setattr(cli, "run_capture", lambda store, **kwargs:
                        run_capture(store, now=NOW, fetcher=feeds, **kwargs))
    cli.main()
    captured = capsys.readouterr()
    assert json.loads(captured.out)["created"] is True and captured.err == ""
    original = output.read_bytes()
    cli = _capture_cli(monkeypatch, store, output, LATER)
    def no_fetch(_):
        raise AssertionError("reuse must not fetch")
    monkeypatch.setattr(cli, "run_capture", lambda store, **kwargs:
                        run_capture(store, now=LATER, fetcher=no_fetch, **kwargs))
    cli.main()
    captured = capsys.readouterr()
    assert json.loads(captured.out)["created"] is False and captured.err == ""
    assert output.read_bytes() == original and fake.puts == 1


def test_capture_cli_after_cutoff_logs_safe_reason_and_still_fails(monkeypatch, tmp_path, capsys):
    fake = FakeGitHub()
    output = tmp_path / "late.json"
    cli = _capture_cli(monkeypatch, ReferenceCheckpointStore(fake, REPO), output, LATER)
    def no_fetch(_):
        raise AssertionError("late capture must not fetch")
    monkeypatch.setattr(cli, "run_capture", lambda store, **kwargs:
                        run_capture(store, now=LATER, fetcher=no_fetch, **kwargs))
    with pytest.raises(SystemExit) as failure:
        cli.main()
    assert failure.value.code == "daily_reference_checkpoint_failed"
    captured = capsys.readouterr()
    assert captured.out == ""
    assert json.loads(captured.err) == {
        "stage": "capture_window", "reason_code": "capture_after_cutoff",
        "current_utc_timestamp": "2026-09-23T01:10:00Z",
        "configured_cutoff": "2026-09-23T00:30:00Z",
    }
    assert fake.puts == 0 and not output.exists()


@pytest.mark.parametrize("error,reason", [
    (CheckpointError("github_api_unavailable"), "github_api_unavailable"),
    (CheckpointError("secret=DO_NOT_LOG header=private response=raw /Users/private"), "checkpoint_failure"),
    (ValueError("secret=DO_NOT_LOG header=private response=raw /Users/private"), "validation_failed"),
    (KeyError("DO_NOT_LOG"), "required_field_missing"),
])
def test_capture_cli_never_logs_exception_payload(monkeypatch, tmp_path, capsys, error, reason):
    cli = _capture_cli(monkeypatch, object(), tmp_path / "unused.json", NOW)
    def fail(*args, **kwargs):
        raise error
    monkeypatch.setattr(cli, "run_capture", fail)
    with pytest.raises(SystemExit) as failure:
        cli.main()
    assert failure.value.code == "daily_reference_checkpoint_failed"
    captured = capsys.readouterr()
    record = json.loads(captured.err)
    assert record["reason_code"] == reason
    assert set(record) == {"stage", "reason_code", "current_utc_timestamp", "configured_cutoff"}
    assert all(text not in captured.out + captured.err for text in (
        "DO_NOT_LOG", "header=", "response=", "/Users/private"))


def test_morning_cli_binding_and_reuse_unchanged(monkeypatch, tmp_path, capsys):
    import src.daily_reference.checkpoint_cli as cli
    fake = FakeGitHub()
    store = ReferenceCheckpointStore(fake, REPO)
    now = datetime(2026, 9, 4, 0, 10, tzinfo=timezone.utc)
    ecb = ECB.replace(b"2026-09-22", b"2026-09-03")
    h15 = H15.replace(b"2026-09-22", b"2026-09-03").replace(b"September 22", b"September 03").replace(b"Sep<br>18", b"Sep<br>01").replace(b"Sep<br>21", b"Sep<br>02")
    reference = collect(now=now, fetcher=lambda url: h15 if url == H15_URL else ecb)
    store.create_or_get("capture", build_capture(reference, captured_at="2026-09-04T00:10:00Z"),
                        run_id=801, head_sha=SHA)
    report_path = tmp_path / "report.json"
    report_path.write_bytes(canonical_bytes(morning_candidate()))
    output = tmp_path / "sidecar.json"
    monkeypatch.setattr(cli, "store_from_environment", lambda: store)
    monkeypatch.setenv("GITHUB_RUN_ID", "900")
    monkeypatch.setenv("GITHUB_SHA", SHA)
    monkeypatch.setattr("sys.argv", ["checkpoint_cli", "morning", "--morning-report", str(report_path),
                                    "--public-out", str(output)])
    cli.main()
    captured = capsys.readouterr()
    assert json.loads(captured.out)["created"] is True and captured.err == ""
    original = output.read_bytes()
    cli.main()
    captured = capsys.readouterr()
    assert json.loads(captured.out)["created"] is False and captured.err == ""
    assert output.read_bytes() == original and fake.puts == 2
