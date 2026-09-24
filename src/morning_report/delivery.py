"""Public-safe delivery status for the fixed Morning Report."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .baseline import instant, target_date, validate_public
from .store import _json_bytes

VERSION = 'morning_delivery_v1'
STATUSES = {'created', 'reused', 'pending_source', 'failed', 'unavailable'}
RETRY_SCHEDULES = {'30 0 * * *': 0, '6 1 * * *': 1}
FAILURES = {'source_inputs_missing', 'source_unavailable_no_checkpoint',
            'morning_minimum_useful_not_met', 'source_manifest_invalid',
            'checkpoint_unavailable', 'checkpoint_invalid', 'delivery_failed'}


def retry_count_for_schedule(schedule):
    if schedule and schedule not in RETRY_SCHEDULES:
        raise ValueError('unknown Morning Report schedule')
    return RETRY_SCHEDULES.get(schedule, 0)


def make_status(slot, *, status, attempted_at, retry_count, report=None,
                failure_code=None):
    date=target_date(slot).isoformat()
    if status not in STATUSES or type(retry_count) is not int or not 0 <= retry_count <= 1:
        raise ValueError('invalid Morning delivery state')
    now=instant(attempted_at)
    if now<instant(slot):
        raise ValueError('attempt before Morning slot')
    ready=status in {'created','reused'}
    if ready:
        validate_public(report)
        if report['baseline_for_date']!=date or report['data_status']=='unavailable':
            raise ValueError('invalid delivered Morning Report')
        if failure_code is not None:
            raise ValueError('success has failure code')
        summary={'state':'ready','eligible_top_items':len(report['content']['top_items']),
                 'source_report_date':report['source_report_date'],
                 'source_freshness_status':report['freshness_status']}
    else:
        if report is not None or failure_code not in FAILURES:
            raise ValueError('invalid Morning delivery failure')
        summary={'state':'not_ready','eligible_top_items':0,
                 'source_report_date':None,'source_freshness_status':'unknown'}
    result={'schema_version':VERSION,'report_date':date,'status':status,
            'report_id':report['report_id'] if ready else None,
            'created_at':report['generated_at'] if ready else None,
            'last_attempt_at':now.isoformat().replace('+00:00','Z'),
            'retry_count':retry_count,'reused':status=='reused',
            'public_artifact_available':ready,'failure_code':failure_code,
            'source_readiness_summary':summary,
            'source_run_id':report['source_run_id'] if ready else None,
            'public_artifact_sha256':hashlib.sha256(_json_bytes(report)).hexdigest() if ready else None}
    validate_status(result, report=report)
    return result


def validate_status(value, *, report=None):
    fields={'schema_version','report_date','status','report_id','created_at',
            'last_attempt_at','retry_count','reused','public_artifact_available',
            'failure_code','source_readiness_summary','source_run_id','public_artifact_sha256'}
    if not isinstance(value,dict) or set(value)!=fields or value['schema_version']!=VERSION:
        raise ValueError('invalid Morning delivery fields')
    if value['status'] not in STATUSES or type(value['retry_count']) is not int or not 0 <= value['retry_count'] <= 1:
        raise ValueError('invalid Morning delivery state')
    if target_date(value['report_date']+'T00:30:00Z').isoformat()!=value['report_date']:
        raise ValueError('invalid Morning delivery date')
    instant(value['last_attempt_at'])
    summary=value['source_readiness_summary']
    if not isinstance(summary,dict) or set(summary)!={'state','eligible_top_items','source_report_date','source_freshness_status'}:
        raise ValueError('invalid Morning readiness summary')
    if (summary['state'] not in {'ready','not_ready'} or
            type(summary['eligible_top_items']) is not int or not 0 <= summary['eligible_top_items'] <= 3 or
            summary['source_freshness_status'] not in {'current','stale','unknown'} or
            summary['source_report_date'] is not None and (
                not isinstance(summary['source_report_date'],str) or
                len(summary['source_report_date'])!=10)):
        raise ValueError('invalid Morning readiness values')
    ready=value['status'] in {'created','reused'}
    if ready:
        if report is None:
            raise ValueError('published Morning status needs report')
        validate_public(report)
        if (not value['public_artifact_available'] or value['reused']!=(value['status']=='reused') or
                value['failure_code'] is not None or value['report_id']!=report['report_id'] or
                value['report_date']!=report['baseline_for_date'] or
                value['created_at']!=report['generated_at'] or
                value['source_run_id']!=report['source_run_id'] or
                value['public_artifact_sha256']!=hashlib.sha256(_json_bytes(report)).hexdigest() or
                summary['state']!='ready' or summary['eligible_top_items']!=len(report['content']['top_items'])):
            raise ValueError('Morning delivery/report mismatch')
        instant(value['created_at'])
    elif (value['public_artifact_available'] or value['reused'] or
          value['failure_code'] not in FAILURES or summary['state']!='not_ready' or
          any(value[k] is not None for k in ('report_id','created_at','source_run_id','public_artifact_sha256'))):
        raise ValueError('invalid unavailable Morning status')
    return value


def write_status(path, status):
    target=Path(path)
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_bytes(_json_bytes(status))


def main():
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--status',type=Path,default=Path('docs/data/morning_delivery_status.json'))
    parser.add_argument('--report',type=Path,default=Path('docs/data/morning_report_public.json'))
    args=parser.parse_args()
    status=json.loads(args.status.read_text())
    report=json.loads(args.report.read_text()) if status.get('public_artifact_available') else None
    validate_status(status,report=report)
    if report is None and args.report.exists():
        raise ValueError('unavailable status alongside report')
    print(status['status'])


if __name__=='__main__':
    main()
