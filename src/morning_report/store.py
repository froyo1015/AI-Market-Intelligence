"""Create-only dated archive and safe public projection."""
from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from .baseline import build, public_projection, target_date, validate, validate_public


def _json_bytes(value):
    return (json.dumps(value,ensure_ascii=False,sort_keys=True,indent=2)+'\n').encode('utf-8')


def _read(path):
    value=json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(value,dict):
        raise ValueError('archive JSON must be an object')
    return value


def _create_only(path, payload):
    path.parent.mkdir(parents=True,exist_ok=True)
    fd,temporary=tempfile.mkstemp(prefix='.morning-pending-',dir=path.parent)
    try:
        with os.fdopen(fd,'wb') as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        try:
            os.link(temporary,path)
            created=True
        except FileExistsError:
            created=False
        if created:
            parent_fd=os.open(path.parent,os.O_RDONLY)
            try:os.fsync(parent_fd)
            finally:os.close(parent_fd)
        return created
    finally:
        os.unlink(temporary)


class MorningArchive:
    def __init__(self,root):
        self.root=Path(root)

    def paths(self,report_date):
        # target_date already validates ISO syntax via a UTC/local slot; callers
        # can only address one validated calendar-day path.
        datetime.strptime(report_date,'%Y-%m-%d')
        folder=self.root/report_date[:4]/report_date
        return folder/'morning_report.json',folder/'morning_report_public.json'

    def get(self,report_date):
        private,_=self.paths(report_date)
        if not private.is_file():return None
        report=_read(private)
        validate(report)
        if report['report_date']!=report_date:
            raise ValueError('archive report date mismatch')
        return report

    def create_or_get(self,candidate):
        validate(candidate)
        private,_=self.paths(candidate['report_date'])
        if not _create_only(private,_json_bytes(candidate)):
            report=self.get(candidate['report_date'])
            if report is None:
                raise ValueError('archive winner missing after collision')
            return report,False
        return candidate,True

    def public(self,report):
        validate(report)
        _,path=self.paths(report['report_date'])
        projection=public_projection(report)
        if not _create_only(path,_json_bytes(projection)):
            existing=_read(path)
            validate_public(existing)
            if existing!=projection:
                raise ValueError('public baseline conflict; existing file remains unchanged')
        return projection


def run(archive,scheduled_at,daily_path,top_path,manifest_path,generated_at=None,
        sample_only=False):
    report_date=target_date(scheduled_at).isoformat()
    existing=archive.get(report_date)
    if existing is not None:
        return existing,archive.public(existing),False
    daily_bytes=Path(daily_path).read_bytes()
    top_bytes=Path(top_path).read_bytes()
    daily=json.loads(daily_bytes)
    top=json.loads(top_bytes)
    manifest=_read(Path(manifest_path))
    report=build(daily,top,manifest,daily_bytes,top_bytes,scheduled_at,
                 generated_at or datetime.now(timezone.utc).isoformat(),sample_only=sample_only)
    stored,created=archive.create_or_get(report)
    return stored,archive.public(stored),created
