from copy import deepcopy
import json
from pathlib import Path

import pytest

from src.brief.intelligence_renderer import render_daily_market_brief
from src.data.freshness import enrich_artifact_freshness
from src.evaluation.minimum_useful_status import (
    build_minimum_useful_status, run_minimum_useful_status_pipeline,
    validate_minimum_useful_status,
)
from src.intelligence.composer import build_daily_intelligence_artifact
from src.top_intelligence.selector import build_top_intelligence_artifact
from tests.test_cross_asset_signals import NOW
from tests.test_daily_intelligence import _four_inputs


ROOT=Path(__file__).resolve().parents[1]
CONTRACT=json.loads((ROOT/'minimum-useful-gate-contract.json').read_text())
NOW_TEXT=NOW.isoformat().replace('+00:00','Z')


def _enriched_inputs(stale_assets=None, market_classes=None):
    b0,s0,r0,k0=_four_inputs(stale_assets=stale_assets)
    b=enrich_artifact_freshness(b0)
    s=enrich_artifact_freshness(s0,[b])
    r=enrich_artifact_freshness(r0,[b,s])
    k=enrich_artifact_freshness(k0,[b,s,r])
    d0=build_daily_intelligence_artifact(b,s,r,k,now=NOW).to_dict()
    d=enrich_artifact_freshness(d0,[b,s,r,k])
    t0=build_top_intelligence_artifact(d,now=NOW).to_dict()
    t=enrich_artifact_freshness(t0,[d])
    symbols=market_classes or [('SPY','equity'),('BTC-USD','crypto'),('ETH-USD','crypto'),
                               ('GOLD','commodity'),('EURUSD','forex'),('USDJPY','forex')]
    market=enrich_artifact_freshness({
        'schema_version':'1.0','artifact_type':'market_snapshot','generated_at':NOW_TEXT,
        'status':'complete','records':[{'symbol':symbol,'asset_type':kind,'status':'success',
        'timestamp':NOW_TEXT,'source':'fixture'} for symbol,kind in symbols]})
    macro=enrich_artifact_freshness({
        'schema_version':'1.0','artifact_type':'macro_snapshot','generated_at':NOW_TEXT,
        'status':'complete','records':[{'symbol':'DXY','status':'success','timestamp':NOW_TEXT,
        'source':'fixture'}]})
    brief=render_daily_market_brief(d,t).markdown
    return {'market_snapshot':market,'macro_snapshot':macro,'evidence_bundle':b,
        'market_signals':s,'market_regime':r,'risk_monitor':k,'daily_intelligence':d,
        'top_intelligence':t,'daily_market_brief':brief,
        'generation_metadata':{'generation_mode':'deterministic_fallback'}}


def _build(artifacts, publication=True):
    return build_minimum_useful_status(artifacts,CONTRACT,evaluated_at=NOW_TEXT,
                                       publication_validated=publication)


def test_useful_degraded_is_not_treated_as_false():
    result=_build(_enriched_inputs())
    assert result['system_health']['state']=='healthy'
    assert result['product_usefulness']['state']=='useful'
    assert result['overall_status']=='degraded'
    assert result['minimum_useful'] is True
    assert 'ai_generation_deterministic_fallback' in result['explicit_limitations']


def test_healthy_but_not_useful_and_degraded_not_useful():
    artifacts=_enriched_inputs(market_classes=[('BTC-USD','crypto'),('ETH-USD','crypto')])
    result=_build(artifacts)
    assert result['system_health']['state']=='healthy'
    assert result['product_usefulness']['state']=='unusable'
    assert not result['minimum_useful']
    three=_enriched_inputs(market_classes=[('BTC-USD','crypto'),('GOLD','commodity'),('EURUSD','forex')])
    result=_build(three)
    assert result['product_usefulness']['state']=='degraded'
    assert result['overall_status']=='degraded'
    assert not result['minimum_useful']


def test_provenance_failure_fails_closed():
    artifacts=_enriched_inputs()
    artifacts['top_intelligence']['items'][0]['headline']='tampered'
    result=_build(artifacts)
    assert not result['provenance_integrity']
    assert result['overall_status']=='unusable'
    assert not result['minimum_useful']


def test_freshness_integrity_failure_fails_closed():
    artifacts=_enriched_inputs()
    artifacts['market_snapshot']['age_seconds']=-1
    result=_build(artifacts)
    assert not result['freshness_integrity']
    assert result['overall_status']=='unusable'


def test_missing_risk_class_and_insufficient_breadth():
    no_risk=_enriched_inputs(market_classes=[('F1','forex'),('F2','forex'),('F3','forex'),
        ('G1','commodity'),('G2','commodity')])
    result=_build(no_risk)
    assert not result['criteria']['risk_asset_class_coverage']['passed']
    assert result['product_usefulness']['state']=='degraded'
    one_class=_enriched_inputs(market_classes=[(f'C{i}','crypto') for i in range(6)])
    result=_build(one_class)
    assert not result['criteria']['asset_class_coverage']['passed']
    assert result['product_usefulness']['state']=='unusable'


def test_justified_unavailable_regime_is_preserved():
    result=_build(_enriched_inputs(stale_assets={'SPY','QQQ','VIX'}))
    assert result['criteria']['regime']['state']=='unavailable'
    assert result['criteria']['regime']['passed']
    assert 'regime_unavailable' in result['explicit_limitations']


def test_publication_failure_affects_system_not_market_facts():
    result=_build(_enriched_inputs(),publication=False)
    assert result['system_health']['state']=='unusable'
    assert result['product_usefulness']['state']=='useful'
    assert result['overall_status']=='unusable'


def test_pipeline_writes_identical_valid_private_and_public_artifacts(tmp_path):
    artifacts=_enriched_inputs();paths={}
    for name,value in artifacts.items():
        suffix='.md' if name=='daily_market_brief' else '.json'
        path=tmp_path/(name+suffix)
        path.write_text(value if isinstance(value,str) else json.dumps(value))
        paths[name]=path
    private=tmp_path/'out.json';public=tmp_path/'docs/data/out.json'
    result=run_minimum_useful_status_pipeline(paths,private,public,
        contract_path=ROOT/'minimum-useful-gate-contract.json',evaluated_at=NOW_TEXT)
    assert json.loads(private.read_text())==result==json.loads(public.read_text())
    validate_minimum_useful_status(result)


def test_validator_rejects_unverified_close_count_and_unknown_fields():
    result=_build(_enriched_inputs())
    changed=deepcopy(result);changed['verified_latest_session_assets_counted']=1
    with pytest.raises(ValueError,match='unverified'):
        validate_minimum_useful_status(changed)
    changed=deepcopy(result);changed['raw_response']='forbidden'
    with pytest.raises(ValueError,match='fields'):
        validate_minimum_useful_status(changed)
