"""Workflow candidate entry point for the immutable Morning Report checkpoint."""
import argparse
import json
import os
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from .baseline import target_date
from .checkpoint import CheckpointError, run_checkpoint, store_from_environment
from .store import MorningArchive


def scheduled_slot(explicit, *, now=None):
    if explicit:
        target_date(explicit)
        return explicit
    current=(now or datetime.now(ZoneInfo('Asia/Taipei'))).astimezone(ZoneInfo('Asia/Taipei'))
    # GitHub does not provide a reliable scheduled-fire timestamp to the job.
    # Refuse a next-day/very-late execution rather than guessing its date.
    if not (8 <= current.hour < 21) or (current.hour == 8 and current.minute < 30):
        raise CheckpointError('scheduled_slot_ambiguous_or_too_late')
    return current.replace(hour=8,minute=30,second=0,microsecond=0).isoformat()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scheduled-at',help='explicit 08:30 Asia/Taipei slot for manual recovery')
    parser.add_argument('--source-root',type=Path,default=Path('work/morning-source'))
    parser.add_argument('--archive-root',type=Path,default=Path('work/morning-reports'))
    parser.add_argument('--public-out',type=Path,default=Path('docs/data/morning_report_public.json'))
    args=parser.parse_args()
    try:
        slot=scheduled_slot(args.scheduled_at)
        args.public_out.unlink(missing_ok=True)
        source=next((folder for folder in (args.source_root/'src/output',args.source_root)
                     if (folder/'daily_intelligence.json').is_file()),args.source_root)
        result=run_checkpoint(store_from_environment(),slot,MorningArchive(args.archive_root),
                              source/'daily_intelligence.json',source/'top_intelligence.json',
                              source/'run_manifest.json',args.public_out,
                              creator_run_id=int(os.environ['GITHUB_RUN_ID']),
                              head_sha=os.environ['GITHUB_SHA'])
        if os.environ.get('GITHUB_OUTPUT'):
            with Path(os.environ['GITHUB_OUTPUT']).open('a') as output:
                output.write('created='+str(result.created).lower()+'\n')
        print(json.dumps(dict(report_id=result.public_report['report_id'],
                              report_date=result.public_report['baseline_for_date'],
                              creator_run_id=result.creator_run_id,created=result.created),sort_keys=True))
    except (CheckpointError, KeyError, ValueError, FileNotFoundError) as error:
        # Do not print API responses, headers, token values, or local paths.
        reason=error.reason if isinstance(error,CheckpointError) else 'morning_checkpoint_failed'
        raise SystemExit(reason) from None


if __name__=='__main__':
    main()
