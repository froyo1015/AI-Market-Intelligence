"""Executable design examples only; no production validator or integration."""
import copy
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from src.evaluation.session_recency import evaluate_session_recency
from tests.test_session_recency import observation, schedule


def design_decision(item, calendar):
    """Test oracle: trusts explicitly synthetic finality attestations only here."""
    if not item or item.get('source_status') != 'success':
        return 'unavailable'
    if item.get('symbol') != 'SPY' or item.get('venue') != 'ARCX':
        return 'unverified_session_observation'
    result = evaluate_session_recency(item, calendar)
    try:
        stamp = datetime.fromisoformat(item['source_timestamp'].replace('Z','+00:00'))
        if stamp.astimezone(ZoneInfo('America/New_York')).date().isoformat() != item['session_id']:
            return 'unverified_session_observation'
    except (ValueError, KeyError):
        return 'unverified_session_observation'
    if result['session_recency'] == 'superseded_session':
        return 'stale_source'
    if (result['session_recency'] in {'latest_validated_close','prior_close_during_open'}
            and item.get('price_basis') == 'unadjusted_regular_session_close'):
        return 'verified_latest_session_close'
    return 'unverified_session_observation'


def examples():
    cases = [
        ('friday_open','2026-09-11T15:00:00Z','10','verified_latest_session_close'),
        ('friday_exact_close_pending','2026-09-11T20:00:00Z','11','unverified_session_observation'),
        ('friday_after_close','2026-09-11T20:06:00Z','11','verified_latest_session_close'),
        ('saturday','2026-09-12T15:00:00Z','11','verified_latest_session_close'),
        ('sunday','2026-09-13T15:00:00Z','11','verified_latest_session_close'),
        ('monday_preopen','2026-09-14T13:29:00Z','11','verified_latest_session_close'),
        ('monday_open_previous_close_only','2026-09-14T14:00:00Z','11','verified_latest_session_close'),
        ('holiday','2026-09-07T15:00:00Z','04','verified_latest_session_close'),
        ('stale_yahoo_open','2026-09-14T15:00:00Z','10','stale_source'),
        ('timestamp_mismatch','2026-09-14T13:00:00Z','11','unverified_session_observation'),
        ('yahoo_without_finality','2026-09-14T13:00:00Z','11','unverified_session_observation'),
        ('adjusted_close','2026-09-14T13:00:00Z','11','unverified_session_observation'),
        ('failed_source','2026-09-14T13:00:00Z','11','unavailable'),
    ]
    rows=[]
    for name,now,day,expected in cases:
        item=observation(now,day)
        item.update(symbol='SPY',venue='ARCX',price_basis='unadjusted_regular_session_close')
        if name=='timestamp_mismatch':item['source_timestamp']='2026-09-10T04:00:00Z'
        if name=='yahoo_without_finality':item['finality']='unknown'
        if name=='adjusted_close':item['price_basis']='adjusted_daily_close'
        if name=='failed_source':item['source_status']='failed'
        rows.append(dict(name=name,input=item,calendar=schedule(),expected=expected))
    early=copy.deepcopy(rows[2]);early['name']='early_close_EST'
    early['calendar']={'version':'synthetic_early_close_v1','source':'NYSE calendar',
        'known_at':'2026-11-01T00:00:00Z','valid_from':'2026-11-27T00:00:00Z',
        'valid_until':'2026-11-28T00:00:00Z','sessions':[
            {'id':'2026-11-27','open':'2026-11-27T14:30:00Z','close':'2026-11-27T18:00:00Z'}]}
    early['input'].update(session_id='2026-11-27',source_timestamp='2026-11-27T05:00:00Z',
        interval_end='2026-11-27T18:00:00Z',available_at='2026-11-27T18:01:00Z',
        retrieved_at='2026-11-27T18:05:00Z',generated_at='2026-11-27T18:06:00Z',age_seconds=47160)
    rows.append(early)
    return rows


@pytest.mark.parametrize('row',examples(),ids=lambda r:r['name'])
def test_design_examples(row):
    original=copy.deepcopy(row['input'])
    assert design_decision(row['input'],row['calendar'])==row['expected']
    assert row['input']==original
    assert row['input']['freshness_status']=='stale'


def test_contract_and_replay_artifact():
    root=Path(__file__).resolve().parents[1]
    contract=json.loads((root/'market-close-contract.json').read_text())
    assert not contract['production_enabled']
    assert contract['price_policy']['approved_yahoo_finality_policy'] is None
    result=json.loads((root/'market-close-replay-results.json').read_text())
    assert result['scenarios']==[{'name':r['name'],'result':design_decision(r['input'],r['calendar']),
                                 'expected':r['expected']} for r in examples()]
