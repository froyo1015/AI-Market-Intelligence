import copy
import pytest
from src.evaluation.beta_readiness import CHECKS, build, validate


def checks():
    # Synthetic gate fixtures, not claims about live readiness.
    return [{'id':k,'status':'pass','scope':'local','finding':'Offline test fixture',
             'evidence':['fixture:test']} for k in CHECKS]


def test_complete_ready_fixture_and_validation():
    r=build(checks(),'2026-09-11T08:00:00Z')
    assert r['beta_status']=='ready' and validate(r)
    assert r['production_enablement'] is False


@pytest.mark.parametrize('status',['fail','unknown'])
def test_critical_failure_or_unknown_blocks(status):
    c=checks(); next(x for x in c if x['id']=='mobile_readiness')['status']=status
    r=build(c,'2026-09-11T08:00:00Z')
    assert r['beta_status']=='blocked'


def test_partial_noncritical_condition():
    c=checks(); next(x for x in c if x['id']=='source_availability')['status']='warn'
    assert build(c,'2026-09-11T08:00:00Z')['beta_status']=='conditional'


def test_missing_evidence_and_missing_category_rejected():
    c=checks(); c[0]['evidence']=[]
    with pytest.raises(ValueError):build(c,'2026-09-11T08:00:00Z')
    with pytest.raises(ValueError):build(checks()[:-1],'2026-09-11T08:00:00Z')


def test_tampered_verdict_and_enablement_rejected():
    c=checks(); c[0]['status']='warn'
    r=build(c,'2026-09-11T08:00:00Z')
    bad=copy.deepcopy(r); bad['beta_status']='ready'
    assert not validate(bad)
    bad=copy.deepcopy(r); bad['production_enablement']=True
    assert not validate(bad)
