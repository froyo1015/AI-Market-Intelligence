"""Review-only manual Morning Report generation; no scheduler registration."""
import argparse
import json
from pathlib import Path

from .store import MorningArchive, run


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scheduled-at',required=True,help='08:30 Asia/Taipei slot as ISO timestamp')
    parser.add_argument('--daily',type=Path,default=Path('src/output/daily_intelligence.json'))
    parser.add_argument('--top',type=Path,default=Path('src/output/top_intelligence.json'))
    parser.add_argument('--manifest',type=Path,default=Path('src/output/run_manifest.json'))
    parser.add_argument('--archive-root',type=Path,default=Path('work/morning-reports'))
    args=parser.parse_args()
    report,public,created=run(MorningArchive(args.archive_root),args.scheduled_at,
                              args.daily,args.top,args.manifest)
    print(json.dumps(dict(report_id=report['report_id'],report_date=report['report_date'],
                          created=created,status=report['data_status'],
                          public_report_id=public['report_id'])))


if __name__=='__main__':
    main()
