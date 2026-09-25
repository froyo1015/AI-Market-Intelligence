import assert from 'node:assert/strict';
import {test} from 'node:test';
import {decideRecovery, executeRecovery, sha256,
  verifyCanonicalCheckpoint} from '../../src/morning_report/watchdog_core.mjs';

const base = {
  now: '2026-09-26T00:55:00Z', reportDate: '2026-09-26',
  checkpoint: 'missing', publicReport: 'missing', deliveryStatus: 'missing',
  activeRun: false, repository: 'froyo1015/AI-Market-Intelligence',
  workflow: '.github/workflows/daily_market_brief.yml',
  source: {repository: 'froyo1015/AI-Market-Intelligence',
    workflow: '.github/workflows/daily_market_brief.yml', branch: 'main',
    status: 'success', runId: 123, artifactId: 456,
    completedAt: '2026-09-25T06:40:08Z'},
};

test('existing Morning checkpoint causes no dispatch, even if Pages lags', async () => {
  let calls = 0;
  for (const publicReport of ['matching', 'missing']) {
    const decision = decideRecovery({...base, checkpoint: 'valid', publicReport});
    const result = await executeRecovery(decision, {claimOnce: async () => {calls++;},
      dispatch: async () => {calls++;}}, {dryRun: false});
    assert.equal(result.status, 'no_action');
  }
  assert.equal(calls, 0);
});

test('missing Morning would dispatch once and atomic claim prevents duplicates', async () => {
  const decision = decideRecovery(base);
  assert.equal(decision.action, 'dispatch');
  assert.equal((await executeRecovery(decision, {}, {dryRun: true})).status, 'would_dispatch');
  const claimed = new Set();
  let dispatches = 0;
  const deps = {claimOnce: async date => {
    if (claimed.has(date)) return false;
    claimed.add(date); return true;
  }, dispatch: async () => {dispatches++; return {workflowRunId: 999};}};
  assert.equal((await executeRecovery(decision, deps, {dryRun: false})).status, 'dispatched');
  assert.equal((await executeRecovery(decision, deps, {dryRun: false})).status, 'already_attempted');
  assert.equal(dispatches, 1);
  assert.equal(decideRecovery({...base, publicReport: 'prior_day'}).action, 'dispatch');
});

test('fails closed for active run, post-cutoff source, wrong date and late runtime', () => {
  assert.equal(decideRecovery({...base, activeRun: true}).reason, 'workflow_active');
  assert.equal(decideRecovery({...base, source: {...base.source,
    completedAt: '2026-09-26T00:31:00Z'}}).reason, 'no_verified_pre_cutoff_source');
  assert.equal(decideRecovery({...base, reportDate: '2026-09-25'}).reason, 'wrong_report_date');
  assert.equal(decideRecovery({...base, now: '2026-09-26T05:00:00Z'}).reason,
    'outside_recovery_window');
  assert.equal(decideRecovery({...base, checkpoint: 'invalid'}).reason, 'checkpoint_invalid');
});

test('failed dispatch consumes the one claim and exposes normalized failure', async () => {
  const claim = new Set();
  const decision = decideRecovery(base);
  const deps = {claimOnce: async date => {
    if (claim.has(date)) return false;
    claim.add(date); return true;
  }, dispatch: async () => {throw new Error('secret-bearing provider detail');}};
  assert.equal((await executeRecovery(decision, deps, {dryRun: false})).status,
    'dispatch_failed');
  assert.equal((await executeRecovery(decision, deps, {dryRun: false})).status,
    'already_attempted');
});

test('existing checkpoint needs dated content, unique archive commit and trusted creator run', async () => {
  const date = '2026-09-26';
  const headSha = 'a'.repeat(40);
  const report = {version: 'morning_report_v1', report_type: 'morning',
    baseline_for_date: date, generated_at: '2026-09-26T00:35:00Z',
    baseline_timestamp: '2026-09-26T08:30:00+08:00', timezone: 'Asia/Taipei',
    report_id: `morning_${date}_0123456789abcdef0123`, data_status: 'partial',
    freshness_status: 'stale', source_run_id: 111,
    source_artifact_refs: [{artifact: 'daily_intelligence.json', sha256: 'b'.repeat(64)}],
    source_report_date: date, immutable_for_day: true, sample_only: false,
    content: {top_items: [], overnight_highlights: []}};
  const bytes = Buffer.from(JSON.stringify(report));
  const digest = await sha256(bytes);
  const record = {path: `2026/${date}/morning_report_public.json`, type: 'file',
    encoding: 'base64', content: bytes.toString('base64')};
  const message = ['morning-checkpoint:v1', date,
    'froyo1015/AI-Market-Intelligence', 'main',
    '.github/workflows/daily_market_brief.yml', '222', headSha, digest].join('|');
  const creator = {id: 222, path: '.github/workflows/daily_market_brief.yml',
    head_branch: 'main', head_sha: headSha,
    head_repository: {full_name: 'froyo1015/AI-Market-Intelligence'},
    repository: {full_name: 'froyo1015/AI-Market-Intelligence'}};
  const getJson = async path => path.startsWith('/commits?') ?
    [{commit: {message}}] : creator;
  assert.equal((await verifyCanonicalCheckpoint(record, date, getJson)).state, 'valid');
  assert.equal((await verifyCanonicalCheckpoint(record, date,
    async path => path.startsWith('/commits?') ? [{commit: {message: message + 'x'}}] : creator)).state,
  'invalid');
  assert.equal((await verifyCanonicalCheckpoint(record, date,
    async path => path.startsWith('/commits?') ? [{commit: {message}}] :
      {...creator, head_sha: 'c'.repeat(40)})).state, 'invalid');
  assert.equal((await verifyCanonicalCheckpoint({...record,
    content: Buffer.from(JSON.stringify({...report, sample_only: true})).toString('base64')},
  date, getJson)).state, 'invalid');
  await assert.rejects(verifyCanonicalCheckpoint(record, date,
    async () => {throw new Error('github_read_unavailable');}), /github_read_unavailable/);
});
