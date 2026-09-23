"""Offline GitHub API contract tests; no network or production writes."""
import base64
import copy
import hashlib
import json
import re
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from src.morning_report.baseline import build, public_projection
from src.morning_report.checkpoint import (
    CheckpointError, GitHubCheckpointStore, run_checkpoint,
)
from src.morning_report.checkpoint_cli import scheduled_slot
from src.morning_report.store import MorningArchive, _json_bytes

ROOT=Path('src/output')
SLOT='2026-09-04T00:30:00Z'
NOW='2026-09-04T00:32:00Z'
REPO='froyo1015/AI-Market-Intelligence'
SHA='a'*40


def public_candidate():
    db=(ROOT/'daily_intelligence.json').read_bytes()
    tb=(ROOT/'top_intelligence.json').read_bytes()
    report=build(json.loads(db),json.loads(tb),
                 json.loads((ROOT/'run_manifest.json').read_bytes()),
                 db,tb,SLOT,NOW)
    return public_projection(report)


class FakeGitHub:
    def __init__(self):
        self.branch=True
        self.file=None
        self.message=None
        self.run_id=801
        self.run_branch='main'
        self.run_workflow='.github/workflows/daily_market_brief.yml'
        self.run_repo=REPO
        self.artifacts=[]
        self.fail_put=False
        self.fail_read=False
        self.puts=0
        self.history_count=1
        self.race_winner=None

    def request(self, method, path, body=None):
        if self.fail_read and method=='GET':
            raise CheckpointError('github_api_unavailable')
        if '/git/ref/heads/morning-reports' in path:
            return (200,{'ref':'refs/heads/morning-reports'}) if self.branch else (404,None)
        if '/actions/artifacts?' in path:
            return 200,{'total_count':len(self.artifacts),'artifacts':self.artifacts}
        if '/actions/runs/' in path:
            return 200,dict(path=self.run_workflow,head_branch=self.run_branch,
                            head_sha=SHA,head_repository={'full_name':self.run_repo},
                            repository={'full_name':REPO})
        if '/commits?' in path:
            return 200,[{'commit':{'message':self.message}}]*self.history_count
        if '/contents/' in path and method=='GET':
            if self.file is None:return 404,None
            record=dict(path='2026/2026-09-04/morning_report_public.json',type='file',
                        encoding='base64',content=base64.b64encode(self.file).decode())
            return 200,record
        if '/contents/' in path and method=='PUT':
            self.puts+=1
            if self.fail_put:return 409,None
            if self.race_winner is not None:
                self.file,self.message=self.race_winner
                self.race_winner=None
                return 409,None
            if self.file is not None:return 422,None
            assert body['branch']=='morning-reports' and 'sha' not in body
            self.file=base64.b64decode(body['content'])
            self.message=body['message']
            return 201,{}
        raise AssertionError((method,path))


def store(fake):
    return GitHubCheckpointStore(fake,REPO)


def create(fake):
    return store(fake).create_or_get(public_candidate(),creator_run_id=801,head_sha=SHA)


def test_missing_checkpoint_first_creation_and_valid_reuse():
    fake=FakeGitHub()
    first=create(fake)
    assert first.created and first.creator_run_id==801 and fake.puts==1
    second=create(fake)
    assert not second.created and second.public_report==first.public_report and fake.puts==1


def test_retry_after_failed_first_attempt():
    fake=FakeGitHub();fake.fail_put=True
    with pytest.raises(CheckpointError,match='checkpoint_conflict_unresolved'):
        create(fake)
    assert fake.file is None
    fake.fail_put=False
    assert create(fake).created


def test_cross_run_restore_skips_source_and_intraday_regeneration(tmp_path):
    fake=FakeGitHub();first=create(fake)
    output=tmp_path/'morning_report_public.json'
    recovered=run_checkpoint(store(fake),SLOT,MorningArchive(tmp_path/'archive'),
        tmp_path/'missing-daily',tmp_path/'missing-top',tmp_path/'missing-manifest',
        output,creator_run_id=900,head_sha=SHA,
        generated_at='2026-09-04T09:00:00Z')
    assert not recovered.created and recovered.creator_run_id==801
    assert recovered.public_report==first.public_report==json.loads(output.read_text())
    assert fake.puts==1


def test_corrupt_and_modified_checkpoint_fail_closed():
    fake=FakeGitHub();create(fake)
    fake.file=b'{broken'
    with pytest.raises(CheckpointError,match='checkpoint_corrupt'):store(fake).discover('2026-09-04')
    fake=FakeGitHub();create(fake);fake.history_count=2
    with pytest.raises(CheckpointError,match='checkpoint_history_modified'):store(fake).discover('2026-09-04')


@pytest.mark.parametrize('field,value',[
    ('run_branch','other'),('run_workflow','.github/workflows/other.yml'),
    ('run_repo','other/repository')])
def test_wrong_branch_workflow_repository_rejected(field,value):
    fake=FakeGitHub();create(fake);setattr(fake,field,value)
    with pytest.raises(CheckpointError,match='creator_run_identity_mismatch'):
        store(fake).discover('2026-09-04')


def test_expired_or_orphan_artifact_fails_closed():
    fake=FakeGitHub()
    fake.artifacts=[{'name':'morning-report-checkpoint-2026-09-04','expired':True}]
    with pytest.raises(CheckpointError,match='orphan_artifact_expired'):
        store(fake).discover('2026-09-04')
    fake.artifacts[0]['expired']=False
    with pytest.raises(CheckpointError,match='orphan_artifact_without_archive'):
        store(fake).discover('2026-09-04')
    fake=FakeGitHub();fake.branch=False
    with pytest.raises(CheckpointError,match='archive_branch_missing'):
        store(fake).discover('2026-09-04')


def test_duplicate_writer_conflict_loads_existing_winner():
    original=FakeGitHub();winner=create(original)
    # A second writer sees absence, then another writer creates the date file
    # just before its PUT; the loser must load the validated winner.
    fake=FakeGitHub();fake.race_winner=(original.file,original.message)
    loser=store(fake).create_or_get(copy.deepcopy(winner.public_report),creator_run_id=900,head_sha=SHA)
    assert not loser.created and loser.creator_run_id==801 and fake.puts==1


def test_next_day_rollover_is_distinct_key():
    assert GitHubCheckpointStore.dated_path('2026-09-04') != GitHubCheckpointStore.dated_path('2026-09-05')
    assert scheduled_slot('2026-09-05T00:30:00Z')=='2026-09-05T00:30:00Z'
    with pytest.raises(CheckpointError,match='invalid_report_date'):
        store(FakeGitHub()).discover('../2026-09-05')


def test_slot_timezone_and_ambiguous_schedule():
    taipei=ZoneInfo('Asia/Taipei')
    assert scheduled_slot(None,now=datetime(2026,9,4,8,40,tzinfo=taipei)).startswith('2026-09-04T08:30')
    with pytest.raises(CheckpointError,match='scheduled_slot_ambiguous_or_too_late'):
        scheduled_slot(None,now=datetime(2026,9,5,0,5,tzinfo=taipei))


def test_public_only_payload_no_token_or_raw_response():
    fake=FakeGitHub();create(fake)
    artifact=json.loads(fake.file)
    assert artifact==public_candidate()
    assert fake.file==_json_bytes(artifact)
    for term in (b'/Users/',b'raw_response',b'Authorization',b'GITHUB_TOKEN'):
        assert term not in fake.file
    assert not re.search(rb'\bsk-[A-Za-z0-9]{16,}\b',fake.file)


def test_sample_cannot_be_persisted_and_transport_failure_does_not_generate(tmp_path):
    fake=FakeGitHub()
    sample=copy.deepcopy(public_candidate());sample['sample_only']=True
    with pytest.raises(CheckpointError,match='sample_cannot_be_persisted'):
        store(fake).create_or_get(sample,creator_run_id=801,head_sha=SHA)
    unavailable=copy.deepcopy(public_candidate());unavailable['data_status']='unavailable'
    with pytest.raises(CheckpointError,match='source_unavailable_no_checkpoint'):
        store(fake).create_or_get(unavailable,creator_run_id=801,head_sha=SHA)
    assert fake.file is None
    fake.fail_read=True
    with pytest.raises(CheckpointError,match='github_api_unavailable'):
        run_checkpoint(store(fake),SLOT,MorningArchive(tmp_path/'archive'),
                       tmp_path/'missing',tmp_path/'missing',tmp_path/'missing',
                       tmp_path/'public.json',creator_run_id=801,head_sha=SHA)
    assert not (tmp_path/'public.json').exists()


def test_documented_reuse_sample_matches_validated_projection():
    sample=json.loads(Path('samples/morning_checkpoint_reuse.json').read_text())
    public=public_candidate()
    assert sample['simulation_only'] is True
    assert sample['report_id']==public['report_id']
    assert sample['public_projection_sha256']==hashlib.sha256(_json_bytes(public)).hexdigest()
    assert sample['first_run']['creator_run_id']==sample['later_run']['creator_run_id']
    assert sample['later_run']['created'] is False


def test_workflow_candidate_stays_inactive_and_after_public_cleanup():
    candidate=Path('docs/workflow-candidates/morning-report-checkpoint.yml')
    text=candidate.read_text()
    assert not str(candidate).startswith('.github/workflows/')
    assert text.index('Download pre-cutoff Morning Report source') < text.index(
        'Existing "Regenerate intelligence pipeline" step runs here')
    assert text.index('Existing "Regenerate intelligence pipeline" step runs here') < text.index(
        'Discover or create fixed Morning Report checkpoint')
    assert 'docs/data/morning_report_public.json' in text
    assert 'retention-days: 30' in text


def test_production_workflow_checkpoint_order_permissions_and_utc_schedule():
    text=Path('.github/workflows/daily_market_brief.yml').read_text()
    assert 'cron: "30 0 * * *"' in text
    assert 'contents: write # create-only date file' in text
    assert text.index('Download pre-cutoff Morning Report source') < text.index(
        'Regenerate intelligence pipeline')
    assert text.index('Regenerate intelligence pipeline') < text.index(
        'Discover or create fixed Morning Report checkpoint')
    assert text.index('Discover or create fixed Morning Report checkpoint') < text.index(
        'Upload GitHub Pages artifact')
    assert 'retention-days: 30' in text
    assert 'cancel-in-progress: false' in text
