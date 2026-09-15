import copy
from datetime import datetime
import json
from pathlib import Path

import pytest

from src.evaluation.session_recency import evaluate_session_recency


def schedule():
    return {'version':'review_fixture_v1', 'source':'https://www.nyse.com/trade/hours-calendars',
            'known_at':'2026-09-01T00:00:00Z', 'valid_from':'2026-09-04T00:00:00Z',
            'valid_until':'2026-09-15T00:00:00Z',
            'sessions':[{'id':f'2026-09-{d}', 'open':f'2026-09-{d}T13:30:00Z',
                         'close':f'2026-09-{d}T20:00:00Z'} for d in ['03','04','08','09','10','11','14']]}


def observation(now, day='11'):
    return {'source_timestamp':f'2026-09-{day}T04:00:00Z',
            'retrieved_at':f'2026-09-{day}T20:05:00Z', 'generated_at':now,
            'age_seconds':(datetime.fromisoformat(now.replace('Z','+00:00'))-datetime.fromisoformat(f'2026-09-{day}T04:00:00+00:00')).total_seconds(), 'freshness_status':'stale', 'source_status':'success',
            'session_id':f'2026-09-{day}', 'interval_end':f'2026-09-{day}T20:00:00Z',
            'available_at':f'2026-09-{day}T20:01:00Z',
            'finality':'validated_final_close', 'finality_reference':'synthetic_test_attestation'}


SCENARIOS = [
    ('friday_open','2026-09-11T15:00:00Z','10','prior_close_during_open'),
    ('friday_after_close','2026-09-11T20:06:00Z','11','latest_validated_close'),
    ('saturday','2026-09-12T15:00:00Z','11','latest_validated_close'),
    ('sunday','2026-09-13T15:00:00Z','11','latest_validated_close'),
    ('monday_preopen','2026-09-14T13:29:59Z','11','latest_validated_close'),
    ('monday_open','2026-09-14T13:30:00Z','11','prior_close_during_open'),
    ('labor_day','2026-09-07T15:00:00Z','04','latest_validated_close'),
    ('stale_open','2026-09-14T15:00:00Z','10','superseded_session'),
    ('immediate_close_not_received','2026-09-11T20:00:00Z','10','superseded_session'),
]


@pytest.mark.parametrize('name,now,day,expected',SCENARIOS)
def test_session_replay(name, now, day, expected):
    item=observation(now,day); original=copy.deepcopy(item)
    result=evaluate_session_recency(item,schedule())
    assert result['session_recency']==expected
    assert item==original
    assert all(result[k]==v for k,v in item.items())
    assert result['freshness_status']=='stale'
    assert result['usable_as_current'] is False
    assert evaluate_session_recency(item,schedule())==result


@pytest.mark.parametrize('field,value',[
    ('finality','unknown'), ('finality_reference',None),
    ('available_at','2026-09-15T00:00:00Z'),
    ('retrieved_at','2026-09-15T00:00:00Z'),
    ('source_timestamp','2026-09-15T00:00:00Z'),
])
def test_unknown_or_future_evidence_cannot_be_accepted(field,value):
    item=observation('2026-09-14T13:00:00Z');item[field]=value
    assert evaluate_session_recency(item,schedule())['session_recency']=='unknown'


def test_failure_and_missing_calendar():
    item=observation('2026-09-14T13:00:00Z');item['source_status']='failed'
    assert evaluate_session_recency(item,schedule())['session_recency']=='unavailable'
    assert evaluate_session_recency(item,{})['session_recency']=='unknown'
    calendar=schedule();calendar['known_at']='2026-09-15T00:00:00Z'
    assert evaluate_session_recency(item,calendar)['session_recency']=='unknown'


def test_scenario_artifact_matches_replay():
    records=json.loads((Path(__file__).resolve().parents[1]/'session-freshness-scenarios.json').read_text())
    for row in records['scenarios']:
        assert evaluate_session_recency(row['input'],records['schedule'])==row['output']
