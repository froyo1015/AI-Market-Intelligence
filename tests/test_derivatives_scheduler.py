import copy
import json
import shutil
from pathlib import Path

import pytest

from test_derivatives_readiness import sample
from test_binance_funding_adapter import run as failed_funding
from src.intelligence import evidence_boundary
from src.shadow.derivatives import checkpoint
from src.shadow.derivatives.scheduler import run, fact_index
from src.shadow.derivatives.archive import history


class Collected:
    def __init__(self, artifact):
        self.artifact = artifact

    def collect(self, request, secrets):
        assert request.metrics[0] in ("funding_rate", "open_interest")


@pytest.fixture
def root(tmp_path, monkeypatch):
    monkeypatch.setattr(evidence_boundary, "SHADOW_ROOT", tmp_path)
    return tmp_path


def scheduled(root, day, name=None, funding=None):
    request = sample(day, archive_request=True)
    adapters = [Collected(funding if funding is not None else request["funding"][0]), Collected(request["oi"][0])]
    return run(root / "history", root / (name or f"run-{day}"), request["daily"], request["upstream"],
               "test", clock=lambda: request["cutoff"], adapters=adapters)


def test_daily_append_and_replay_after_accumulation(root):
    scheduled(root, 9)
    r = scheduled(root, 10)
    samples, inv = history(root / "history", "2026-09-10T00:03:00.123Z")
    assert len(samples) == 2 and inv["active_entries"] == 2
    assert r["status"] == "insufficient_history"
    assert len(fact_index(root / "history")["facts"]) == 8
    assert (root / "run-10/derivatives_readiness.json").exists()


def test_duplicate_observation_dedup_preserves_receipts(root):
    scheduled(root, 10)
    scheduled(root, 10, name="retry")
    index = fact_index(root / "history")
    assert len(index["facts"]) == 4
    assert all(f["observation_refs"] and f["archive_refs"] for f in index["facts"])
    assert len(list((root / "history").glob("*/*.json"))) == 1
    request = sample(10, archive_request=True)
    run(root / "history", root / "later", request["daily"], request["upstream"], "later",
        clock=lambda: "2026-09-10T00:03:00.123Z",
        adapters=[Collected(request["funding"][0]), Collected(request["oi"][0])])
    index = fact_index(root / "history")
    assert len(index["facts"]) == 4
    assert all(len(f["archive_refs"]) == 2 for f in index["facts"])


def test_missing_provider_archived(root):
    failure = failed_funding({"exchange": (403, b"private-body")})[0]
    r = scheduled(root, 10, funding=failure)
    assert r["status"] == "blocked"
    manifest = json.loads((root / "run-10/shadow_run.json").read_text())
    assert manifest["provider_status"] == ["unavailable", "available"]
    assert "private-body" not in json.dumps(manifest)
    assert len(history(root / "history", "2026-09-10T00:03:00.123Z")[0]) == 1


def test_readiness_update_without_enablement(root):
    for day in range(4, 11):
        r = scheduled(root, day)
    assert r["status"] == "passing" and r["production_enabled"] is False


def test_checkpoint_restore_replays_all_before_append(root, monkeypatch):
    scheduled(root, 10)
    # Storage/replay unit test only; real encryption exercised separately with GPG.
    monkeypatch.setattr(checkpoint, "crypt", lambda source, target, decrypt=False: shutil.copyfile(source, target))
    checkpoint.seal(root / "history", root / "test.gpg", root / "run-10")
    checkpoint.restore(root / "test.gpg", root / "restored")
    assert fact_index(root / "restored") == fact_index(root / "history")
    payload = json.loads((root / "test.gpg").read_text())
    bad = copy.deepcopy(payload["entries"][0])
    bad["entry_hash"] = "bad"
    payload["entries"].append(bad)
    (root / "bad.gpg").write_text(json.dumps(payload))
    with pytest.raises(ValueError):
        checkpoint.restore(root / "bad.gpg", root / "bad-restore")
    assert not (root / "bad-restore").exists()


def test_missing_checkpoint_secret(monkeypatch):
    monkeypatch.delenv("DERIVATIVES_ARCHIVE_PASSPHRASE", raising=False)
    with pytest.raises(ValueError, match="credential unavailable"):
        checkpoint.secret()


def test_crypto_secret_only_on_stdin(root, monkeypatch):
    from types import SimpleNamespace
    key = "fixture-credential-" * 3
    monkeypatch.setenv("DERIVATIVES_ARCHIVE_PASSPHRASE", key)
    monkeypatch.setenv("GITHUB_TOKEN", "fixture-token")
    def invoke(command, **kwargs):
        assert key not in str(command)
        assert kwargs["input"] == (key + "\n").encode()
        assert "DERIVATIVES_ARCHIVE_PASSPHRASE" not in kwargs["env"]
        assert "GITHUB_TOKEN" not in kwargs["env"]
        return SimpleNamespace(returncode=1)
    monkeypatch.setattr(checkpoint.subprocess, "run", invoke)
    with pytest.raises(ValueError, match="checkpoint cryptography failed"):
        checkpoint.crypt(root / "input", root / "output")


@pytest.mark.skipif(shutil.which("gpg") is None, reason="GnuPG unavailable locally; required on Actions")
def test_real_checkpoint_encryption_and_wrong_key(root, monkeypatch):
    monkeypatch.setenv("DERIVATIVES_ARCHIVE_PASSPHRASE", "offline-fixture-only-" * 3)
    scheduled(root, 10)
    checkpoint.seal(root / "history", root / "secure.gpg")
    assert b"body_base64" not in (root / "secure.gpg").read_bytes()
    checkpoint.restore(root / "secure.gpg", root / "restored")
    assert fact_index(root / "restored") == fact_index(root / "history")
    monkeypatch.setenv("DERIVATIVES_ARCHIVE_PASSPHRASE", "wrong-fixture-key-" * 3)
    with pytest.raises(ValueError):
        checkpoint.restore(root / "secure.gpg", root / "wrong")
    assert not (root / "wrong").exists()


def test_workflow_upload_is_ciphertext_only():
    workflow = Path(".github/workflows/derivatives_shadow.yml").read_text()
    assert 'cron: "15 1 * * *"' in workflow
    assert "cancel-in-progress: false" in workflow
    upload = workflow.split("- name: Persist ciphertext only")[1]
    assert "path: outputs/shadow/derivatives/scheduled/checkpoint.gpg" in upload
    assert "pages" not in workflow.lower() and "src.orchestration" not in workflow
    assert "src.telegram" not in workflow and "OPENAI" not in workflow
