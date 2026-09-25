"""Morning delivery status and bounded retry contract."""
import json
from datetime import datetime
from pathlib import Path

import pytest

from src.morning_report.baseline import build, public_projection
from src.morning_report.baseline import _eligible
from src.data.freshness import enrich_artifact_freshness
from src.morning_report.delivery import (
    RETRY_SCHEDULES, make_status, retry_count_for_schedule, validate_status,
)
from src.morning_report.retry_preflight import retry_needed
from src.morning_report.store import _json_bytes

ROOT=Path('src/output')
SLOT='2026-09-04T00:30:00Z'


def report():
    db=(ROOT/'daily_intelligence.json').read_bytes()
    tb=(ROOT/'top_intelligence.json').read_bytes()
    value=build(json.loads(db),json.loads(tb),
                json.loads((ROOT/'run_manifest.json').read_text()),
                db,tb,SLOT,'2026-09-04T00:32:00Z')
    return public_projection(value)


def test_created_and_reused_share_report_identity_and_hash():
    payload=report()
    first=make_status(SLOT,status='created',attempted_at='2026-09-04T00:34:00Z',
                      retry_count=0,report=payload)
    second=make_status(SLOT,status='reused',attempted_at='2026-09-04T01:06:00Z',
                       retry_count=1,report=payload)
    assert first['report_id']==second['report_id']
    assert first['public_artifact_sha256']==second['public_artifact_sha256']
    assert first['created_at']==second['created_at'] and second['reused']
    assert validate_status(first,report=payload)==first


def test_pending_and_unavailable_never_claim_report():
    pending=make_status(SLOT,status='pending_source',attempted_at='2026-09-04T00:42:00Z',
                        retry_count=1,failure_code='source_unavailable_no_checkpoint')
    final=make_status(SLOT,status='unavailable',attempted_at='2026-09-04T01:06:00Z',
                      retry_count=1,failure_code='morning_minimum_useful_not_met')
    for value in (pending,final):
        assert not value['public_artifact_available'] and value['report_id'] is None
        assert value['source_readiness_summary']['state']=='not_ready'
    final['public_artifact_available']=True
    with pytest.raises(ValueError):validate_status(final)


def test_retry_schedule_is_bounded_and_uses_taipei_fixed_slot():
    assert sorted(RETRY_SCHEDULES.values())==[0,1]
    assert retry_count_for_schedule('6 1 * * *')==1
    assert retry_count_for_schedule('')==0
    with pytest.raises(ValueError):retry_count_for_schedule('9 1 * * *')
    text=Path('.github/workflows/daily_market_brief.yml').read_text()
    for schedule in RETRY_SCHEDULES:
        assert ('cron: "'+schedule+'"') in text
    assert text.index('Discover or create fixed Morning Report checkpoint') < text.index(
        'Validate and report Morning delivery state') < text.index('Upload GitHub Pages artifact')
    assert 'docs/data/morning_delivery_status.json' in text
    assert 'needs.morning_retry_preflight.outputs.needed' in text
    assert 'unset OPENAI_API_KEY' in text


def test_pages_deploy_does_not_inherit_skipped_preflight():
    text=Path('.github/workflows/daily_market_brief.yml').read_text()
    deploy=text.split('\n  deploy:\n',1)[1]
    assert 'needs: generate' in deploy
    assert "if: ${{ !cancelled() && needs.generate.result == 'success' }}" in deploy


def test_next_day_status_has_distinct_date_and_report():
    payload=report()
    first=make_status(SLOT,status='created',attempted_at='2026-09-04T00:33:00Z',
                      retry_count=0,report=payload)
    later=make_status('2026-09-05T00:30:00Z',status='pending_source',
                      attempted_at='2026-09-05T00:34:00Z',retry_count=0,
                      failure_code='source_inputs_missing')
    assert first['report_date']!=later['report_date']
    assert later['report_id'] is None


def test_item_freshness_reassessed_at_morning_cutoff():
    leaf=enrich_artifact_freshness({
        'artifact_type':'item_freshness',
        'generated_at':'2026-09-03T00:01:00Z',
        'observed_at':['2026-09-02T00:00:00Z'],
        'retrieved_at':'2026-09-03T00:00:30Z',
    },[{'retrieved_at':'2026-09-03T00:00:30Z'}],stale_after_seconds=172800)
    top={'freshness_items':{'items':{'top_x':leaf}}}
    item={'item_id':'top_x','validation_status':'validated','freshness_status':'current',
          'type':'cross_asset_signal','timestamps':{'observed_at':['2026-09-02T00:00:00Z']}}
    assert _eligible(item,datetime.fromisoformat('2026-09-03T23:30:00+00:00'),top)
    assert not _eligible(item,datetime.fromisoformat('2026-09-04T00:30:00+00:00'),top)
    assert not _eligible(item,datetime.fromisoformat('2026-09-03T23:30:00+00:00'),
                         {'freshness_items':{'items':{}}})


def test_retry_preflight_skips_published_checkpoint_and_repairs_missing_public():
    payload=report()
    class Store:
        def __init__(self, existing):self.existing=existing
        def discover(self, date):
            assert date=='2026-09-04'
            return self.existing
    checkpoint=type('Checkpoint',(),{'public_report':payload})()
    url='https://example.invalid/data/morning_report_public.json'
    status_url='https://example.invalid/data/morning_delivery_status.json'
    status=make_status(SLOT,status='created',attempted_at='2026-09-04T00:34:00Z',
                       retry_count=0,report=payload)
    def valid_public(target):
        return _json_bytes(payload) if target==url else _json_bytes(status)
    assert not retry_needed(Store(checkpoint),'2026-09-04',public_url=url,
                            status_url=status_url,read_public=valid_public)
    assert retry_needed(Store(checkpoint),'2026-09-04',public_url=url,
                        status_url=status_url,read_public=lambda _: b'prior-day')
    assert retry_needed(Store(checkpoint),'2026-09-04',public_url=url,
                        status_url=status_url,read_public=lambda target: _json_bytes(payload)
                        if target==url else b'not-json')
    assert retry_needed(Store(None),'2026-09-04',public_url=url,status_url=status_url,
                        read_public=lambda _: pytest.fail('no public fetch without checkpoint'))
