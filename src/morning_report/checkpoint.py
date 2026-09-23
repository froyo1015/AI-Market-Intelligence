"""Create-only GitHub checkpoint for the public Morning Report projection.

The dated file on a separate branch is the authority. Actions artifacts are
retained as supplementary checkpoints, never as the date lock.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from .baseline import target_date, validate_public
from .store import _json_bytes, run as build_local

MAX_REPORT_BYTES = 256_000
WORKFLOW = '.github/workflows/daily_market_brief.yml'
ARCHIVE_BRANCH = 'morning-reports'


class CheckpointError(ValueError):
    """A normalized, secret-free checkpoint failure."""

    def __init__(self, reason):
        self.reason = reason
        super().__init__(reason)


class GitHubTransport:
    """Runtime-only GITHUB_TOKEN boundary; response bodies are never logged."""

    def __init__(self, token, *, api_url='https://api.github.com'):
        if not token:
            raise CheckpointError('missing_runtime_token')
        self._token = token
        self._api_url = api_url.rstrip('/')

    def request(self, method, path, body=None):
        data = None if body is None else json.dumps(body, separators=(',', ':')).encode()
        request = Request(self._api_url + path, data=data, method=method, headers={
            'Authorization': 'Bearer ' + self._token,
            'Accept': 'application/vnd.github+json',
            'X-GitHub-Api-Version': '2022-11-28',
            'Content-Type': 'application/json',
        })
        try:
            with urlopen(request, timeout=20) as response:
                return response.status, json.load(response)
        except HTTPError as error:
            # Never include the provider body or headers in logs/artifacts.
            if error.code in (404, 409, 422):
                return error.code, None
            raise CheckpointError('github_api_unavailable') from None
        except (URLError, TimeoutError, ValueError):
            raise CheckpointError('github_api_unavailable') from None


@dataclass(frozen=True)
class Checkpoint:
    public_report: dict
    creator_run_id: int
    created: bool


class GitHubCheckpointStore:
    def __init__(self, transport, repo, *, source_branch='main',
                 archive_branch=ARCHIVE_BRANCH, workflow=WORKFLOW):
        if '/' not in repo or not source_branch or not archive_branch:
            raise CheckpointError('invalid_repository_identity')
        self.transport = transport
        self.repo = repo
        self.source_branch = source_branch
        self.archive_branch = archive_branch
        self.workflow = workflow
        self.base = '/repos/' + quote(repo, safe='/')

    @staticmethod
    def dated_path(report_date):
        return f'{report_date[:4]}/{report_date}/morning_report_public.json'

    def _request(self, method, path, body=None):
        status, payload = self.transport.request(method, self.base + path, body)
        if status not in (200, 201, 404, 409, 422):
            raise CheckpointError('github_api_unavailable')
        return status, payload

    def _branch_exists(self):
        status, ref = self._request('GET', '/git/ref/heads/' + quote(self.archive_branch, safe=''))
        if status != 200 or not isinstance(ref, dict) or ref.get('ref') != 'refs/heads/' + self.archive_branch:
            raise CheckpointError('archive_branch_missing')

    def _creator_run(self, run_id, head_sha):
        status, run = self._request('GET', f'/actions/runs/{run_id}')
        if status != 200 or not isinstance(run, dict):
            raise CheckpointError('creator_run_unavailable')
        if (run.get('path') != self.workflow or
                run.get('head_branch') != self.source_branch or
                run.get('head_sha') != head_sha or
                (run.get('head_repository') or {}).get('full_name') != self.repo or
                (run.get('repository') or {}).get('full_name') != self.repo):
            raise CheckpointError('creator_run_identity_mismatch')

    def _commit_message(self, report_date, run_id, head_sha, digest):
        return '|'.join(('morning-checkpoint:v1', report_date, self.repo,
                         self.source_branch, self.workflow, str(run_id), head_sha, digest))

    def discover(self, report_date):
        if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', report_date):
            raise CheckpointError('invalid_report_date')
        try:
            date.fromisoformat(report_date)
        except ValueError:
            raise CheckpointError('invalid_report_date') from None
        self._branch_exists()
        path = self.dated_path(report_date)
        status, record = self._request('GET', '/contents/' + path + '?ref=' + quote(self.archive_branch, safe=''))
        if status == 404:
            self._check_orphan_artifacts(report_date)
            return None
        if status != 200 or not isinstance(record, dict) or record.get('path') != path or record.get('type') != 'file':
            raise CheckpointError('checkpoint_invalid')
        if record.get('encoding') != 'base64' or not isinstance(record.get('content'), str):
            raise CheckpointError('checkpoint_invalid')
        try:
            raw = base64.b64decode(''.join(record['content'].split()), validate=True)
            if not raw or len(raw) > MAX_REPORT_BYTES:
                raise ValueError('invalid size')
            public = json.loads(raw)
            validate_public(public)
        except (ValueError, TypeError, KeyError, AttributeError):
            raise CheckpointError('checkpoint_corrupt') from None
        if public['baseline_for_date'] != report_date or public['sample_only']:
            raise CheckpointError('checkpoint_date_or_sample_mismatch')
        if public['data_status'] == 'unavailable':
            raise CheckpointError('checkpoint_unavailable_not_valid')
        digest = hashlib.sha256(raw).hexdigest()
        status, commits = self._request('GET', '/commits?sha=' + quote(self.archive_branch, safe='') +
                                        '&path=' + quote(path, safe='') + '&per_page=2')
        if status != 200 or not isinstance(commits, list) or len(commits) != 1:
            raise CheckpointError('checkpoint_history_modified')
        message = commits[0].get('commit', {}).get('message', '')
        pieces = message.split('|')
        if len(pieces) != 8 or not pieces[5].isdigit():
            raise CheckpointError('checkpoint_provenance_invalid')
        expected = self._commit_message(report_date, int(pieces[5]), pieces[6], digest)
        if message != expected:
            raise CheckpointError('checkpoint_provenance_invalid')
        self._creator_run(int(pieces[5]), pieces[6])
        return Checkpoint(public, int(pieces[5]), False)

    def _check_orphan_artifacts(self, report_date):
        name = 'morning-report-checkpoint-' + report_date
        status, result = self._request('GET', '/actions/artifacts?name=' + name + '&per_page=100')
        if status != 200 or not isinstance(result, dict):
            raise CheckpointError('artifact_discovery_unavailable')
        count = result.get('total_count')
        artifacts = result.get('artifacts')
        if not isinstance(count, int) or not isinstance(artifacts, list) or count > len(artifacts):
            raise CheckpointError('artifact_discovery_incomplete')
        if any(artifact.get('name') == name and artifact.get('expired') for artifact in artifacts):
            raise CheckpointError('orphan_artifact_expired')
        if any(artifact.get('name') == name for artifact in artifacts):
            raise CheckpointError('orphan_artifact_without_archive')

    def create_or_get(self, public_report, *, creator_run_id, head_sha):
        validate_public(public_report)
        report_date = public_report['baseline_for_date']
        existing = self.discover(report_date)
        if existing is not None:
            return existing
        if public_report['sample_only']:
            raise CheckpointError('sample_cannot_be_persisted')
        if public_report['data_status'] == 'unavailable':
            raise CheckpointError('source_unavailable_no_checkpoint')
        self._creator_run(creator_run_id, head_sha)
        payload = _json_bytes(public_report)
        if len(payload) > MAX_REPORT_BYTES:
            raise CheckpointError('checkpoint_too_large')
        path = self.dated_path(report_date)
        digest = hashlib.sha256(payload).hexdigest()
        body = dict(message=self._commit_message(report_date, creator_run_id, head_sha, digest),
                    content=base64.b64encode(payload).decode('ascii'), branch=self.archive_branch)
        status, _ = self._request('PUT', '/contents/' + path, body)
        if status == 201:
            winner = self.discover(report_date)
            if winner is None or winner.public_report != public_report:
                raise CheckpointError('checkpoint_write_not_confirmed')
            return Checkpoint(winner.public_report, winner.creator_run_id, True)
        if status in (409, 422):
            winner = self.discover(report_date)
            if winner is None:
                raise CheckpointError('checkpoint_conflict_unresolved')
            return winner
        raise CheckpointError('checkpoint_write_failed')


def run_checkpoint(store, scheduled_at, archive, daily_path, top_path,
                   manifest_path, public_path, *, creator_run_id, head_sha,
                   generated_at=None):
    """Discover first; only build if the dated remote authority is absent."""
    report_date = target_date(scheduled_at).isoformat()
    existing = store.discover(report_date)
    if existing is not None:
        result = existing
    else:
        _, public, _ = build_local(archive, scheduled_at, daily_path, top_path,
                                    manifest_path, generated_at=generated_at)
        result = store.create_or_get(public, creator_run_id=creator_run_id,
                                     head_sha=head_sha)
    target = Path(public_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    # The target is a mutable deployment projection, not the immutable archive.
    target.write_bytes(_json_bytes(result.public_report))
    return result


def store_from_environment():
    repo = os.environ.get('GITHUB_REPOSITORY', '')
    source_branch = os.environ.get('GITHUB_REF_NAME', '')
    if source_branch != 'main':
        raise CheckpointError('wrong_source_branch')
    return GitHubCheckpointStore(GitHubTransport(os.environ.get('GITHUB_TOKEN')),
                                 repo, source_branch=source_branch)
