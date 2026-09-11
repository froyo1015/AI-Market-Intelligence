import copy
import json
import subprocess
from pathlib import Path

import pytest

from src.pages.previous_report import project
from src.pages.intelligence_generator import generate_intelligence_page


def changes(current, previous):
    code="const v=require(process.argv[1]); console.log(JSON.stringify(v.observedChanges(JSON.parse(process.argv[2]),JSON.parse(process.argv[3]))));"
    return json.loads(subprocess.check_output(['node','-e',code,str(Path('src/pages/static/intelligence.js').resolve()),json.dumps(current),json.dumps(previous)],text=True))


def snapshot(day,price,status='success'):
    return {'generated_at':f'2026-09-{day:02d}T12:00:00Z','records':[
        {'symbol':'SPY','price':price,'timestamp':f'2026-09-{day:02d}T10:00:00Z','source':'yahoo_finance','status':status}]}


def test_empty_unavailable_previous_missing():
    assert 'Current market snapshot unavailable' in changes(None,None)[0]
    assert 'Previous available run unavailable' in changes(snapshot(10,100),None)[0]
    assert 'No comparable' in changes({'generated_at':'2026-09-10T12:00:00Z','records':[]},snapshot(9,100))[-1]


def test_stale_observed_change_preserves_provenance():
    c,p=snapshot(10,99,'stale'),snapshot(9,100)
    text=' '.join(changes(c,p))
    assert '100 → 99' in text and 'success → stale' in text
    assert p['records'][0]['timestamp'] in text and c['records'][0]['timestamp'] in text
    assert 'yahoo_finance' in text
    assert all(x not in text.lower() for x in ['caused','buy','sell','bullish','bearish'])


def test_invalid_chronology_and_source():
    assert 'not earlier' in changes(snapshot(9,90),snapshot(10,100))[0]
    c=snapshot(10,90); c['records'][0]['source']='other'
    assert 'No comparable' in changes(c,snapshot(9,100))[-1]


def test_projection_no_raw_fields():
    p=snapshot(9,100); p['secret']='private'; p['records'][0]['receipts']=['private']
    result=project(p)
    assert 'private' not in json.dumps(result)
    assert project(result)==result


def test_mobile_reading_flow_and_audit_preserved():
    page=generate_intelligence_page()
    ids=['executive-summary','what-changed','top-intelligence','markets','risks','audit']
    assert [page.index(f'id="{x}"') for x in ids]==sorted(page.index(f'id="{x}"') for x in ids)
    assert 'grid-template-columns: 1fr' in page
    assert 'overflow-wrap: anywhere' in page
    assert 'id="audit-content"' in page and 'id="derivatives-content"' in page
    assert "script-src 'self'" in page
