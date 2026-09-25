from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from src.morning_report.recovery_guard import validate_recovery


SLOT = '2026-09-26T08:30:00+08:00'
TZ = ZoneInfo('Asia/Taipei')


def at(hour, minute):
    return datetime(2026, 9, 26, hour, minute, tzinfo=TZ)


def test_watchdog_recovery_window_and_same_date():
    assert validate_recovery(SLOT, '2026-09-26', 'missing_checkpoint', now=at(8, 55)) == 'missing_checkpoint'
    for current in (at(8, 44), at(9, 31)):
        with pytest.raises(ValueError, match='bounded window'):
            validate_recovery(SLOT, '2026-09-26', 'missing_checkpoint', now=current)
    with pytest.raises(ValueError, match='current Taipei date'):
        validate_recovery(SLOT, '2026-09-25', 'missing_checkpoint', now=at(8, 55))


def test_manual_validation_cannot_create_a_checkpoint():
    class Store:
        def __init__(self, checkpoint):
            self.checkpoint = checkpoint
        def discover(self, date):
            assert date == '2026-09-26'
            return self.checkpoint
    assert validate_recovery(SLOT, '2026-09-26', 'validate_existing',
                             now=at(10, 0), store=Store(object())) == 'validate_existing'
    with pytest.raises(ValueError, match='existing checkpoint'):
        validate_recovery(SLOT, '2026-09-26', 'validate_existing',
                          now=at(10, 0), store=Store(None))
    with pytest.raises(ValueError, match='same-day window'):
        validate_recovery(SLOT, '2026-09-26', 'validate_existing',
                          now=at(21, 0), store=Store(object()))


def test_missing_or_unknown_inputs_fail_closed():
    assert validate_recovery(SLOT, now=at(8, 55)) is None
    with pytest.raises(ValueError, match='paired'):
        validate_recovery(SLOT, '2026-09-26', '', now=at(8, 55))
    with pytest.raises(ValueError, match='Unknown'):
        validate_recovery(SLOT, '2026-09-26', 'unapproved_reason', now=at(8, 55))
