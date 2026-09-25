"""Fail-closed command boundary for external Morning recovery dispatches."""
from datetime import datetime, time
from zoneinfo import ZoneInfo

from .baseline import target_date


def validate_recovery(slot, report_date='', reason='', *, now=None, store=None):
    if bool(report_date) != bool(reason):
        raise ValueError('Morning recovery inputs must be paired')
    if not reason:
        return None
    today=(now or datetime.now(ZoneInfo('Asia/Taipei'))).astimezone(ZoneInfo('Asia/Taipei'))
    date=target_date(slot).isoformat()
    if report_date != date or today.date().isoformat() != date:
        raise ValueError('Morning recovery must target the current Taipei date')
    if reason == 'missing_checkpoint':
        if not time(8, 45) <= today.time().replace(tzinfo=None) <= time(9, 30):
            raise ValueError('Morning recovery outside bounded window')
    elif reason == 'validate_existing':
        if not time(8, 30) <= today.time().replace(tzinfo=None) < time(21, 0):
            raise ValueError('Morning reuse validation outside same-day window')
        if store is None or store.discover(date) is None:
            raise ValueError('Morning reuse validation requires existing checkpoint')
    else:
        raise ValueError('Unknown Morning recovery reason')
    return reason
