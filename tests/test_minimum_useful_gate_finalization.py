import copy
import json
from pathlib import Path

import pytest

from src.evaluation.minimum_useful_gate import evaluate_gate


ROOT=Path(__file__).resolve().parents[1]
CONTRACT=json.loads((ROOT/'minimum-useful-gate-contract.json').read_text())
REPORT=json.loads((ROOT/'minimum-useful-gate-evaluated-snapshot.json').read_text())


def test_fixed_production_evaluation_is_reproducible():
    assert evaluate_gate(CONTRACT, REPORT['input_snapshot']) == REPORT
    assert REPORT['system_health']['state']=='healthy'
    assert REPORT['product_usefulness']['state']=='useful'
    assert REPORT['overall_state']=='degraded'
    assert REPORT['minimum_useful'] is True


def test_missing_equity_caps_overall_without_fabricating_coverage():
    assert REPORT['criteria']['asset_class_coverage']['missing_declared_classes']==['equity']
    assert REPORT['verified_latest_session_assets_counted']==0
    assert 'missing_current_core_asset_classes:equity' in REPORT['product_usefulness']['reasons']


def test_non_current_asset_cannot_enter_current_coverage():
    snapshot=copy.deepcopy(REPORT['input_snapshot'])
    snapshot['current_core_assets'][0]['freshness_status']='stale'
    with pytest.raises(ValueError,match='non-current'):
        evaluate_gate(CONTRACT,snapshot)


def test_duplicate_symbol_cannot_inflate_count():
    snapshot=copy.deepcopy(REPORT['input_snapshot'])
    snapshot['current_core_assets'].append(copy.deepcopy(snapshot['current_core_assets'][0]))
    with pytest.raises(ValueError,match='distinct'):
        evaluate_gate(CONTRACT,snapshot)


def test_integrity_failure_makes_both_system_and_product_unusable():
    snapshot=copy.deepcopy(REPORT['input_snapshot'])
    snapshot['freshness_integrity']=False
    snapshot['system_checks']['freshness_integrity']=False
    result=evaluate_gate(CONTRACT,snapshot)
    assert result['system_health']['state']=='unusable'
    assert result['product_usefulness']['state']=='unusable'
    assert result['overall_state']=='unusable'
    assert not result['minimum_useful']


def test_content_shortfall_can_be_degraded_without_being_healthy():
    snapshot=copy.deepcopy(REPORT['input_snapshot'])
    snapshot['current_core_assets']=snapshot['current_core_assets'][:3]
    snapshot['current_validated_top_count']=1
    result=evaluate_gate(CONTRACT,snapshot)
    assert result['system_health']['state']=='healthy'
    assert result['product_usefulness']['state']=='degraded'
    assert result['overall_state']=='degraded'
    assert not result['minimum_useful']


def test_regime_unavailable_requires_explicit_justification():
    snapshot=copy.deepcopy(REPORT['input_snapshot'])
    snapshot['regime_valid_or_justified_unavailable']=False
    result=evaluate_gate(CONTRACT,snapshot)
    assert not result['criteria']['regime']['passed']
    assert result['product_usefulness']['state']=='degraded'


def test_six_assets_in_one_class_do_not_satisfy_useful_gate():
    snapshot=copy.deepcopy(REPORT['input_snapshot'])
    snapshot['current_core_assets']=[{'symbol':f'C{i}','asset_class':'crypto','freshness_status':'current'} for i in range(6)]
    result=evaluate_gate(CONTRACT,snapshot)
    assert result['criteria']['core_asset_coverage']['passed']
    assert not result['criteria']['asset_class_coverage']['passed']
    assert result['product_usefulness']['state']=='unusable'


def test_contract_is_promoted_for_reporting_but_does_not_enable_gate_b():
    assert CONTRACT['scope']=='production_reporting'
    assert CONTRACT['production_enabled'] is True
    assert CONTRACT['integration_status']=='review_candidate'
    rules=' '.join(CONTRACT['product_usefulness']['counting_rules'])
    assert 'do not count stale' in rules
    assert 'verified_latest_session_close does not count' in rules
