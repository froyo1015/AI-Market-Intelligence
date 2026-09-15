"""Offline session-recency experiment; never upgrades canonical freshness.

Schedule and final-bar attestations must be supplied explicitly. This is not a
calendar source, quote classifier, or production consumer.
"""
from copy import deepcopy
from datetime import datetime


def _time(value):
    result = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if result.tzinfo is None:
        raise ValueError('timezone required')
    return result


def evaluate_session_recency(observation, schedule):
    result = deepcopy(observation)
    result.update(session_state='unknown', session_recency='unknown',
                  latest_session_id=None, usable_as_current=False)
    try:
        now = _time(observation['generated_at'])
        start, end = _time(schedule['valid_from']), _time(schedule['valid_until'])
        if not start <= now < end or _time(schedule['known_at']) > now:
            return result
        if not schedule.get('version') or not schedule.get('source'):
            return result
        sessions = sorted(schedule['sessions'], key=lambda s: s['open'])
        for i, session in enumerate(sessions):
            if _time(session['open']) >= _time(session['close']):
                raise ValueError('invalid session')
            if i and _time(sessions[i-1]['close']) >= _time(session['open']):
                raise ValueError('overlapping sessions')
        result['session_state'] = 'open' if any(
            _time(s['open']) <= now < _time(s['close']) for s in sessions) else 'closed'
        result['calendar_version'] = schedule['version']
        result['calendar_source'] = schedule['source']
        completed = [s for s in sessions if _time(s['close']) <= now]
        if not completed:
            return result
        latest = completed[-1]
        result['latest_session_id'] = latest['id']
        if observation.get('source_status') != 'success':
            result['session_recency'] = 'unavailable'
            return result
        if (_time(observation['retrieved_at']) > now or
                _time(observation['source_timestamp']) > now):
            return result
        # A bar-date label alone is insufficient: require explicit finality,
        # interval identity, and when that final observation became available.
        if observation.get('finality') != 'validated_final_close':
            return result
        if not observation.get('finality_reference'):
            return result
        close = _time(observation['interval_end'])
        available = _time(observation['available_at'])
        if not close <= available <= _time(observation['retrieved_at']) <= now:
            return result
        matches = observation.get('session_id') == latest['id'] and close == _time(latest['close'])
        if not matches:
            result['session_recency'] = 'superseded_session'
        elif result['session_state'] == 'open':
            result['session_recency'] = 'prior_close_during_open'
        else:
            result['session_recency'] = 'latest_validated_close'
        return result
    except (KeyError, ValueError, TypeError):
        result['session_recency'] = 'unknown'
        return result
