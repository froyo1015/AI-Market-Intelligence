"""Skip the scheduled Morning retry when checkpoint and public bytes agree."""
from __future__ import annotations

import os
import json
from datetime import datetime
from urllib.error import HTTPError, URLError
from urllib.request import urlopen
from zoneinfo import ZoneInfo

from .checkpoint import store_from_environment
from .delivery import validate_status
from .store import _json_bytes


def retry_needed(store, report_date, *, public_url, status_url, read_public=None):
    checkpoint=store.discover(report_date)
    if checkpoint is None:
        return True
    reader=read_public or (lambda url: urlopen(url,timeout=10).read(256_001))
    try:
        public_bytes=reader(public_url)
        if public_bytes!=_json_bytes(checkpoint.public_report):
            return True
        status=json.loads(reader(status_url))
        validate_status(status,report=checkpoint.public_report)
        return status['report_date']!=report_date
    except (HTTPError, URLError, TimeoutError, ValueError, KeyError, TypeError):
        return True


def main():
    repo=os.environ['GITHUB_REPOSITORY']
    owner,name=repo.split('/',1)
    date=datetime.now(ZoneInfo('Asia/Taipei')).date().isoformat()
    public_url=f'https://{owner}.github.io/{name}/data/morning_report_public.json'
    status_url=f'https://{owner}.github.io/{name}/data/morning_delivery_status.json'
    needed=retry_needed(store_from_environment(),date,public_url=public_url,status_url=status_url)
    with open(os.environ['GITHUB_OUTPUT'],'a',encoding='utf-8') as output:
        output.write('needed='+str(needed).lower()+'\n')
    print('morning_retry_needed' if needed else 'morning_already_published')


if __name__=='__main__':
    main()
