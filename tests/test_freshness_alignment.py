import copy
import json
import subprocess
from pathlib import Path

import pytest

from src.data.freshness import enrich_artifact_freshness, validate_freshness_contract
from src.data.item_freshness import build_item_freshness

NOW = '2026-09-14T08:00:00Z'


def top(times, unavailable=False):
    observations = [dict(observation_id=f'obs_{i}', as_of=t, status='success', source_id='src_test') for i,t in enumerate(times)]
    catalog = {'provenance_catalog': {'observation_records': observations,
        'source_records': [{'source_id': 'src_test', 'retrieved_at': NOW}]}}
    domain = {'artifact_type': 'top_intelligence', 'generated_at': NOW,
        'status': 'unavailable' if unavailable else 'partial', 'items': [
            {'item_id': f'item_{i}', 'rank': i+1, 'headline': f'Fact {i}', 'why': 'Observed fact',
             'monitor': 'Same metric', 'type': 'cross_asset_signal', 'total_score': 68-i,
             'freshness_status': 'current', 'validation_status': 'validated',
             'source_refs': ['src_test'], 'evidence_refs': {'observation_ids': [f'obs_{i}'], 'source_ids': ['src_test']}}
            for i in range(len(times))]}
    return enrich_artifact_freshness(domain, [catalog]), catalog


def frontend(artifact, timestamp=NOW):
    return json.loads(subprocess.check_output(['node', '-e',
        'const v=require(process.argv[1]);console.log(JSON.stringify(v.normalizeTopIntelligence(JSON.parse(process.argv[2]),Date.parse(process.argv[3]))));',
        str(Path('src/pages/static/intelligence.js').resolve()), json.dumps(artifact), timestamp], text=True))


@pytest.mark.parametrize('times,expected', [
    (['2026-09-14T04:00:00Z']*2, ['current','current']),
    (['2026-09-11T04:00:00Z']*2, ['stale','stale']),
    (['2026-09-11T04:00:00Z','2026-09-14T04:00:00Z'], ['stale','current']),
])
def test_item_visibility_without_whole_artifact_upgrade(times, expected):
    artifact,_ = top(times)
    validate_freshness_contract(artifact)
    assert artifact['freshness_status'] == ('stale' if 'stale' in expected else 'current')
    model = frontend(artifact)
    assert [i['freshnessStatus'] for i in model['items']] == expected
    assert [i['rank'] for i in model['items']] == [1,2]
    assert [i['score'] for i in model['items']] == [68,67]


def test_unavailable_parent_not_upgraded():
    artifact,_=top(['2026-09-14T04:00:00Z'],unavailable=True)
    assert artifact['freshness_status']=='unavailable'
    assert frontend(artifact)['items']==[]


def test_missing_referenced_record_never_uses_retrieval_as_market_time():
    artifact,catalog=top(['2026-09-14T04:00:00Z'])
    catalog['provenance_catalog']['observation_records']=[]
    artifact['freshness_items']=build_item_freshness(artifact,[catalog])
    assert artifact['freshness_items']['items']['item_0']['freshness_status']=='unavailable'
    assert frontend(artifact)['items']==[]


def test_source_failure_not_upgraded():
    artifact,catalog=top(['2026-09-14T04:00:00Z'])
    catalog['provenance_catalog']['source_records'][0]['status']='unavailable'
    assert build_item_freshness(artifact,[catalog])['items']['item_0']['freshness_status']=='unavailable'


def test_reference_and_receipt_preservation_and_unrelated_source_isolation():
    artifact,catalog=top(['2026-09-14T04:00:00Z'])
    before=copy.deepcopy(artifact['items'])
    catalog['unrelated']={'as_of':'2020-01-01T00:00:00Z'}
    result=enrich_artifact_freshness(artifact,[catalog])
    assert result['freshness_status']=='stale'
    row=result['freshness_items']['items']['item_0']
    assert row['freshness_status']=='current'
    assert row['retrieved_at']==NOW
    assert row['observation_ids']==['obs_0']
    assert result['items']==before


def test_browser_can_downgrade_but_not_upgrade():
    artifact,_=top(['2026-09-14T04:00:00Z'])
    assert frontend(artifact,'2026-09-17T08:00:00Z')['items'][0]['freshnessStatus']=='stale'


def test_invalid_metadata_and_private_fields_rejected():
    artifact,_=top(['2026-09-14T04:00:00Z'])
    artifact['freshness_items']['items']['item_0']['raw_response']='must not publish'
    with pytest.raises(ValueError): validate_freshness_contract(artifact)


def test_impossible_current_age_rejected_by_browser_and_validator():
    artifact,_=top(['2026-09-11T04:00:00Z'])
    artifact['freshness_items']['items']['item_0']['freshness_status']='current'
    with pytest.raises(ValueError): validate_freshness_contract(artifact)
    assert frontend(artifact)['items']==[]


def test_legacy_stale_artifact_remains_conservative():
    artifact,_=top(['2026-09-11T04:00:00Z','2026-09-14T04:00:00Z'])
    del artifact['freshness_items']
    assert frontend(artifact)['items']==[]


def test_retrieval_does_not_refresh_old_observation_in_bundle():
    from tests.test_evidence_consolidation import _observations, NOW as CUTOFF
    from src.consolidation.builder import build_consolidated_evidence_artifact
    from datetime import timedelta
    artifact=_observations()
    artifact['observations'][0]['as_of']=(CUTOFF-timedelta(hours=60)).isoformat().replace('+00:00','Z')
    identifier=artifact['observations'][0]['observation_id']
    result=build_consolidated_evidence_artifact(artifact,None,None,None,now=CUTOFF).to_dict()
    assert any(identifier in b['freshness']['stale_record_ids'] for b in result['bundles'])


def test_enriched_selection_calendar_and_safety():
    from tests.test_top_intelligence import _daily, NOW as CUTOFF
    from tests.test_evidence_consolidation import _calendar
    from src.top_intelligence.selector import build_top_intelligence_artifact, TopIntelligenceSelectionError
    daily=enrich_artifact_freshness(_daily(calendar=_calendar()))
    selected=build_top_intelligence_artifact(daily,now=CUTOFF).to_dict()
    assert any(i['type']=='upcoming_event' for i in selected['items'])
    key=next(iter(daily['freshness_items']['items']))
    daily['freshness_items']['items'][key]['age_seconds']=1
    with pytest.raises(TopIntelligenceSelectionError): build_top_intelligence_artifact(daily,now=CUTOFF)


def test_future_observation_cannot_become_current():
    artifact,_=top(['2026-09-15T04:00:00Z'])
    assert artifact['freshness_items']['items']['item_0']['freshness_status']=='unavailable'
    assert frontend(artifact)['items']==[]


def test_explicit_stale_source_cannot_be_upgraded_by_recent_timestamp():
    artifact,catalog=top(['2026-09-14T04:00:00Z'])
    catalog['provenance_catalog']['observation_records'][0]['status']='stale'
    row=build_item_freshness(artifact,[catalog])['items']['item_0']
    assert row['freshness_status']=='unavailable'
