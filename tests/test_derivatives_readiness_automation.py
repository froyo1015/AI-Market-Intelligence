import copy
import json
from pathlib import Path

from test_derivatives_readiness import sample, AS_OF
from test_derivatives_context_evaluation import inputs
from test_derivatives_scheduler import scheduled
from src.intelligence import evidence_boundary
from src.shadow.derivatives.readiness import assess
from src.pages.derivatives_schema import validate_public


def test_accumulation_missing_days_and_transition():
    history = [sample(d) for d in range(4, 10)]
    before = assess(history, AS_OF)
    assert before['status'] == 'insufficient_history'
    assert before['tracking']['collected_days'] == 6
    assert before['tracking']['missing_days'] == ['2026-09-10']
    history.append(sample(10))
    after = assess(history, AS_OF)
    assert after['status'] == 'passing' and after['production_enabled'] is False
    assert after['tracking']['freshness_pass_rate'] == 1
    assert after['tracking']['provenance_completeness'] == 1
    assert after['tracking']['validation_failures'] == 0


def test_stale_and_invalid_samples_not_hidden():
    b, c = inputs()
    p = {'bundle': b, 'context': c}
    r = assess([p, p], AS_OF)
    assert r['tracking']['sample_count'] == 1
    assert r['tracking']['freshness_pass_rate'] == 0
    assert r['tracking']['provenance_completeness'] == 1
    bad = copy.deepcopy(p)
    bad['context']['derivatives_evidence']['current_facts'][0]['provenance'] = {}
    assert assess([bad], AS_OF)['tracking']['validation_failures'] == 1


def test_scheduler_readiness_public_handoff(tmp_path, monkeypatch):
    monkeypatch.setattr(evidence_boundary, 'SHADOW_ROOT', tmp_path)
    scheduled(tmp_path, 9)
    scheduled(tmp_path, 10)
    directory = tmp_path / 'run-10'
    private = json.loads((directory / 'derivatives_readiness.json').read_text())
    public = json.loads((directory / 'derivatives-shadow.json').read_text())
    assert validate_public(public)
    assert public['readiness']['tracking'] == private['tracking']
    assert public['generated_at'] == private['evaluated_at']
    assert public['readiness']['production_enabled'] is False
    public['readiness']['tracking']['receipts'] = []
    assert not validate_public(public)


def test_pages_handoff_only_sanitized_file():
    workflow = Path('.github/workflows/daily_market_brief.yml').read_text()
    assert "name: 'derivatives-shadow-public'" in workflow
    assert "if not validate_public(payload)" in workflow
    assert 'DERIVATIVES_ARCHIVE_PASSPHRASE' not in workflow
    assert 'checkpoint.gpg' not in workflow
