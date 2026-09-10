import copy
import json

import pytest

from test_derivatives_readiness import sample, AS_OF
from src.intelligence import evidence_boundary
from src.shadow.derivatives.archive import append, history, readiness, replay, build_entry


@pytest.fixture
def root(tmp_path, monkeypatch):
    monkeypatch.setattr(evidence_boundary, "SHADOW_ROOT", tmp_path)
    return tmp_path / "archive"


def test_multi_day_accumulation_and_readiness(root):
    for day in range(4, 11):
        req = sample(day, archive_request=True)
        p = append(root, req)
        assert append(root, req) == p
        assert p.stat().st_mode & 0o077 == 0
    samples, inventory = history(root, AS_OF)
    assert len(samples) == 7 and inventory["active_entries"] == 7
    assert readiness(root, AS_OF)["status"] == "passing"
    assert readiness(root, AS_OF)["production_enabled"] is False


def test_replay_receipts_and_tamper_rejection(root):
    req = sample(10, archive_request=True)
    p = append(root, req)
    entry = json.loads(p.read_text())
    assert entry["request"]["funding"] == req["funding"]
    assert replay(entry)["bundle"] == entry["bundle"]
    bad = copy.deepcopy(entry)
    bad["request"]["funding"][0]["captures"]["BTCUSDT"]["body_base64"] = "AAAA"
    with pytest.raises(ValueError):
        replay(bad)


def test_retention_is_non_destructive(root):
    p = append(root, sample(4, archive_request=True))
    samples, inv = history(root, "2026-10-10T00:03:00.123Z")
    assert samples == [] and inv["cold_entries"] == 1
    assert p.exists() and not inv["deletion_enabled"]
    with pytest.raises(ValueError):
        history(root, AS_OF, retention_days=6)


def test_missing_day_handling(root):
    for day in (4, 5, 6, 8, 9, 10):
        append(root, sample(day, archive_request=True))
    r = readiness(root, AS_OF)
    assert r["status"] == "insufficient_history"
    assert "2026-09-07" in r["archive_inventory"]["missing_dates"]


def test_archive_receipt_time_prevents_backdating(root):
    req = sample(10, archive_request=True)
    req["archived_at"] = "2026-09-11T00:03:00.123Z"
    append(root, req)
    assert history(root, AS_OF)[1]["not_yet_archived_entries"] == 1
    req["archived_at"] = "2026-09-09T00:03:00.123Z"
    with pytest.raises(ValueError):
        build_entry(req)


def test_shadow_path_guard(root):
    with pytest.raises(ValueError):
        append(root.parent.parent / "public", sample(10, archive_request=True))
