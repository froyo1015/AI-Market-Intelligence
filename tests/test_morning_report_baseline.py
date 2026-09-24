import copy
import hashlib
import json
import re
from datetime import datetime
from pathlib import Path

import pytest

from src.morning_report.baseline import (
    _source_current, build, public_projection, target_date, validate, validate_public,
)
from src.morning_report.store import MorningArchive, run

ROOT=Path('src/output')
SLOT='2026-09-04T00:30:00Z'
GENERATED='2026-09-04T00:32:00Z'


def inputs():
    daily_bytes=(ROOT/'daily_intelligence.json').read_bytes()
    top_bytes=(ROOT/'top_intelligence.json').read_bytes()
    manifest=json.loads((ROOT/'run_manifest.json').read_text())
    return json.loads(daily_bytes),json.loads(top_bytes),manifest,daily_bytes,top_bytes


def candidate():
    return build(*inputs(),SLOT,GENERATED,sample_only=True)


def shifted(report, date, slot, generation):
    changed=copy.deepcopy(report)
    changed.update(report_date=date,baseline_for_date=date,
                   baseline_timestamp=slot,generated_at=generation)
    changed.pop('report_id')
    changed['report_id']='morning_'+date+'_'+hashlib.sha256(json.dumps(
        changed,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()[:20]
    validate(changed)
    return changed


def test_normal_scheduled_generation_and_source_linkage():
    report=candidate()
    assert report['report_date']=='2026-09-04' and report['immutable_for_day']
    assert report['source_report_date']=='2026-09-03'
    assert report['source_artifact_refs'][0]['sha256']==hashlib.sha256(inputs()[3]).hexdigest()
    assert report['data_status']=='partial' and len(report['content']['top_items'])==2
    assert all(i['evidence_refs'] and i['source_ids'] for i in report['content']['top_items'])
    assert '隔夜' in report['content']['overnight_note_zh']
    assert all('buy' not in i['headline_zh'].lower() for i in report['content']['top_items'])


def test_first_failure_allows_same_day_recovery(tmp_path):
    archive=MorningArchive(tmp_path)
    with pytest.raises(FileNotFoundError):
        run(archive,SLOT,tmp_path/'missing.json',ROOT/'top_intelligence.json',ROOT/'run_manifest.json',GENERATED)
    assert archive.get('2026-09-04') is None
    report,public,created=run(archive,SLOT,ROOT/'daily_intelligence.json',ROOT/'top_intelligence.json',
                              ROOT/'run_manifest.json',GENERATED)
    assert created and public['report_id']==report['report_id']


def test_retry_and_intraday_rerun_never_overwrite(tmp_path):
    archive=MorningArchive(tmp_path)
    report,created=archive.create_or_get(candidate())
    assert created
    original=(archive.paths('2026-09-04')[0]).read_bytes()
    later=build(*inputs(),SLOT,'2026-09-04T08:00:00Z',sample_only=True)
    stored,created=archive.create_or_get(later)
    assert not created and stored==report
    assert archive.paths('2026-09-04')[0].read_bytes()==original
    first_public=archive.public(report)
    second_public=archive.public(stored)
    assert first_public==second_public


def test_retrieval_after_restart_and_missing_public_rebuild(tmp_path):
    archive=MorningArchive(tmp_path)
    report,_=archive.create_or_get(candidate())
    new_process=MorningArchive(tmp_path)
    restored,projection,created=run(new_process,SLOT,tmp_path/'no-input',tmp_path/'no-top',
        tmp_path/'no-manifest',GENERATED)
    assert not created and restored==report
    assert projection==public_projection(report)


def test_duplicate_candidate_and_corrupt_archive_fail_closed(tmp_path):
    archive=MorningArchive(tmp_path)
    one=candidate()
    archive.create_or_get(one)
    other=copy.deepcopy(one);other['content']['today_market_one_sentence']='another story'
    other.pop('report_id')
    other['report_id']='morning_'+other['report_date']+'_'+hashlib.sha256(json.dumps(
        other,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()[:20]
    assert archive.create_or_get(other)[0]==one
    private,_=archive.paths('2026-09-04')
    # A bad pre-existing file must not be silently replaced by the next attempt.
    private.write_text('{}')
    with pytest.raises(ValueError):archive.create_or_get(one)


def test_next_day_rollover_has_distinct_path(tmp_path):
    archive=MorningArchive(tmp_path)
    first=candidate();archive.create_or_get(first)
    next_day=shifted(first,'2026-09-05','2026-09-05T00:30:00Z','2026-09-05T00:32:00Z')
    second,created=archive.create_or_get(next_day)
    assert created and second['report_id']!=first['report_id']
    assert archive.get('2026-09-04')==first and archive.get('2026-09-05')==second


def test_delay_same_day_allowed_late_next_day_rejected():
    report=build(*inputs(),SLOT,'2026-09-04T15:59:00Z',sample_only=True)
    assert report['baseline_timestamp']==SLOT and report['generated_at']=='2026-09-04T15:59:00Z'
    with pytest.raises(ValueError):build(*inputs(),SLOT,'2026-09-04T16:01:00Z')


def test_taipei_schedule_and_upstream_dst_independent():
    for date in ('2026-01-04','2026-07-04'):
        assert target_date(date+'T00:30:00Z').isoformat()==date
    with pytest.raises(ValueError):target_date('2026-09-04T08:30:00Z')


def test_partial_and_stale_source_distinct():
    report=candidate()
    assert report['data_status']=='partial'
    cutoff=datetime.fromisoformat(SLOT.replace('Z','+00:00'))
    refs=report['source_artifact_refs']
    source=copy.deepcopy(refs)
    for r in source:r['source_timestamp']='2026-08-30T00:00:00Z'
    assert not _source_current(source,({'stale_after_seconds':172800},)*2,cutoff)
    assert _source_current(refs,({'stale_after_seconds':172800},)*2,cutoff)


def test_stale_artifact_aggregate_keeps_current_items_with_warning(monkeypatch):
    monkeypatch.setattr('src.morning_report.baseline._source_current',lambda *_: False)
    report=candidate()
    assert report['source_freshness_status']=='stale'
    assert report['data_status']=='partial'
    assert len(report['content']['top_items'])>=2
    assert any('過期' in text for text in report['content']['known_limitations'])


def test_morning_gate_rejects_insufficient_current_market_items(monkeypatch):
    d,t,m,db,tb=inputs()
    monkeypatch.setattr('src.morning_report.baseline._eligible',
                        lambda item, cutoff, top=None: item.get('rank')==1)
    report=build(d,t,m,db,tb,SLOT,GENERATED,sample_only=True)
    assert report['data_status']=='unavailable'
    assert report['content']['top_items']==[]


def test_optional_calendar_absent_and_old_future_event_excluded():
    report=candidate()
    assert 'calendar' not in report['source_artifact_refs'][0]['artifact']
    assert all(i['source_type']!='upcoming_event' for i in report['content']['top_items'])
    assert report['content']['overnight_highlights']==[]


def test_hash_mismatch_future_input_and_public_safety():
    d,t,m,db,tb=inputs()
    bad=copy.deepcopy(m)
    for module in bad['modules']:
        for artifact in module.get('artifacts',[]):
            if artifact.get('path')=='top_intelligence.json':artifact['sha256']='0'*64
    with pytest.raises(ValueError):build(d,t,bad,db,tb,SLOT,GENERATED)
    with pytest.raises(ValueError):build(d,t,m,db,tb,'2026-09-03T00:30:00Z','2026-09-03T00:32:00Z')
    public=public_projection(candidate())
    serialized=json.dumps(public)
    for marker in ('/Users/','raw_response','Authorization','prompt'):
        assert marker not in serialized
    assert not re.search(r'\bsk-[A-Za-z0-9]{16,}\b',serialized)
    assert public['report_type']=='morning' and public['baseline_for_date']=='2026-09-04'


def test_public_projection_conflict_does_not_overwrite(tmp_path):
    archive=MorningArchive(tmp_path)
    report,_=archive.create_or_get(candidate())
    archive.public(report)
    _,public_path=archive.paths(report['report_date'])
    public_path.write_text('{"wrong":true}')
    with pytest.raises(ValueError):archive.public(report)
    assert public_path.read_text()=='{"wrong":true}'


def test_sample_public_projection_and_extra_field_rejected():
    private=json.loads(Path('samples/morning_report.json').read_text())
    public=json.loads(Path('samples/morning_report_public.json').read_text())
    validate(private)
    validate_public(public)
    assert public_projection(private)==public
    leaked=copy.deepcopy(public);leaked['internal_path']='/private/review'
    with pytest.raises(ValueError):validate_public(leaked)
