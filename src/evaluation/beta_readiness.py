"""Audit-only beta gate. Never changes production configuration."""
import argparse
import json
from datetime import datetime
from pathlib import Path

CHECKS = {
    'actions_success_rate': ('system_health', False),
    'pipeline_completion': ('system_health', False),
    'artifact_generation': ('system_health', True),
    'deployment_status': ('system_health', True),
    'release_parity': ('system_health', True),
    'source_availability': ('data_reliability', False),
    'freshness': ('data_reliability', False),
    'stale_handling': ('data_reliability', True),
    'unavailable_handling': ('data_reliability', True),
    'provenance_completeness': ('evidence_integrity', False),
    'reference_preservation': ('evidence_integrity', True),
    'replay_capability': ('evidence_integrity', False),
    'validation_status': ('evidence_integrity', True),
    'unsupported_claims': ('ai_safety', False),
    'investment_advice': ('ai_safety', True),
    'prediction_logic': ('ai_safety', True),
    'fallback': ('ai_safety', True),
    'secrets': ('public_security', True),
    'raw_responses': ('public_security', True),
    'internal_paths': ('public_security', True),
    'debug_artifacts': ('public_security', True),
    'onboarding': ('user_experience', False),
    'unavailable_ux': ('user_experience', True),
    'mobile_readiness': ('user_experience', True),
}


def require(ok):
    if not ok:
        raise ValueError('invalid beta readiness contract')


def build(checks, assessed_at):
    require(isinstance(assessed_at, str))
    require(datetime.fromisoformat(assessed_at.replace('Z','+00:00')).tzinfo is not None)
    require(isinstance(checks, list) and len(checks) == len(CHECKS))
    require({c['id'] for c in checks} == set(CHECKS))
    for c in checks:
        require(set(c) == {'id','status','scope','finding','evidence'})
        require(c['status'] in ('pass','warn','fail','unknown'))
        require(c['scope'] in ('local','production','mixed'))
        require(isinstance(c['finding'],str) and 0 < len(c['finding']) <= 2000)
        require(isinstance(c['evidence'],list) and bool(c['evidence'])
                and all(isinstance(x,str) and 0 < len(x) <= 500 for x in c['evidence']))
    blockers = sorted(c['id'] for c in checks if CHECKS[c['id']][1] and c['status'] in ('fail','unknown'))
    conditions = sorted(c['id'] for c in checks if c['status'] != 'pass' and c['id'] not in blockers)
    return {'schema_contract':'beta_readiness_v1','policy_id':'limited-public-beta-v1',
            'assessed_at':assessed_at,'beta_status':'blocked' if blockers else 'conditional' if conditions else 'ready',
            'production_enablement':False, 'blockers':blockers,'conditions':conditions,
            'checks':sorted(checks,key=lambda c:c['id'])}


def validate(report):
    try:
        return report == build(report['checks'],report['assessed_at'])
    except (ValueError,KeyError,TypeError,OverflowError):
        return False


def main():
    p=argparse.ArgumentParser(description='Validate an audit report; never enables beta')
    p.add_argument('report')
    args=p.parse_args()
    report=json.loads(Path(args.report).read_text())
    if not validate(report):
        raise SystemExit('Invalid beta readiness report')
    print(report['beta_status'])


if __name__=='__main__':
    main()
