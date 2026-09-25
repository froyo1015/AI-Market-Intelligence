/** Cloudflare Workers Free candidate: one bounded, credential-isolated check. */
import {DurableObject} from 'cloudflare:workers';
import {decideRecovery, executeRecovery, sha256, taipeiDate,
  verifyCanonicalCheckpoint} from '../src/morning_report/watchdog_core.mjs';

const REPO = 'froyo1015/AI-Market-Intelligence';
const WORKFLOW = '.github/workflows/daily_market_brief.yml';
const API = `https://api.github.com/repos/${REPO}`;
const PAGES = 'https://froyo1015.github.io/AI-Market-Intelligence/data';
const HEADERS = {'Accept': 'application/vnd.github+json',
  'X-GitHub-Api-Version': '2022-11-28', 'User-Agent': 'ai-market-morning-watchdog'};

async function api(path, {missingOk = false} = {}) {
  // Public repository metadata needs no credential; keep the secret for dispatch only.
  const response = await fetch(API + path, {headers: HEADERS, cache: 'no-store'});
  if (missingOk && response.status === 404) return null;
  if (!response.ok) throw new Error('github_read_unavailable');
  return response.json();
}

async function publicJson(name) {
  const response = await fetch(`${PAGES}/${name}`, {cache: 'no-store'});
  if (response.status === 404) return null;
  if (!response.ok) throw new Error('pages_read_unavailable');
  try {
    const bytes = new Uint8Array(await response.arrayBuffer());
    return {value: JSON.parse(new TextDecoder('utf-8', {fatal: true}).decode(bytes)),
      digest: await sha256(bytes)};
  } catch { throw new Error('pages_json_invalid'); }
}

async function snapshot(now) {
  const reportDate = taipeiDate(now);
  const path = `${reportDate.slice(0, 4)}/${reportDate}/morning_report_public.json`;
  const record = await api(`/contents/${path}?ref=morning-reports`, {missingOk: true});
  const checkpoint = await verifyCanonicalCheckpoint(record, reportDate, api);
  const [publicReport, deliveryStatus] = await Promise.all([
    publicJson('morning_report_public.json'),
    publicJson('morning_delivery_status.json'),
  ]);
  const reportState = publicReport === null ? 'missing' :
    checkpoint.state === 'valid' && publicReport.digest === checkpoint.digest &&
    publicReport.value.report_id === checkpoint.report.report_id &&
    publicReport.value.baseline_for_date === reportDate ? 'matching' :
    typeof publicReport.value.baseline_for_date === 'string' &&
    publicReport.value.baseline_for_date < reportDate ? 'prior_day' : 'unexpected';
  const statusState = deliveryStatus === null ? 'missing' :
    checkpoint.state === 'valid' && deliveryStatus.value.schema_version === 'morning_delivery_v1' &&
    deliveryStatus.value.report_date === reportDate &&
    ['created', 'reused'].includes(deliveryStatus.value.status) &&
    deliveryStatus.value.report_id === checkpoint.report.report_id &&
    deliveryStatus.value.public_artifact_sha256 === checkpoint.digest &&
    deliveryStatus.value.public_artifact_available === true ? 'matching' : 'unexpected';
  if (checkpoint.state !== 'missing') return {now, reportDate,
    checkpoint: checkpoint.state, publicReport: reportState, deliveryStatus: statusState,
    activeRun: false, source: null, repository: REPO, workflow: WORKFLOW};
  const list = await api(`/actions/workflows/daily_market_brief.yml/runs?branch=main&per_page=30`);
  if (!Array.isArray(list.workflow_runs)) throw new Error('runs_response_invalid');
  const cutoff = Date.parse(`${reportDate}T00:30:00Z`);
  const dateStart = Date.parse(`${reportDate}T00:00:00Z`);
  const trusted = list.workflow_runs.filter(run => run.path === WORKFLOW &&
    run.head_branch === 'main' && run.head_repository?.full_name === REPO &&
    run.repository?.full_name === REPO);
  const activeRun = trusted.some(run => Date.parse(run.created_at) >= dateStart &&
    !['completed', 'cancelled'].includes(run.status));
  let source = null;
  if (!activeRun && ['missing', 'prior_day'].includes(reportState)) {
    for (const run of trusted.filter(run => run.conclusion === 'success' &&
        Date.parse(run.updated_at) <= cutoff).slice(0, 10)) {
      const artifacts = await api(`/actions/runs/${run.id}/artifacts?per_page=100`);
      const expectedName = `daily-market-brief-${run.id}-${run.run_attempt}`;
      const artifact = artifacts.artifacts?.find(item => !item.expired &&
        item.name === expectedName && item.workflow_run?.id === run.id);
      if (artifact) {
        source = {repository: REPO, workflow: WORKFLOW, branch: 'main',
          status: 'success', runId: run.id, artifactId: artifact.id,
          completedAt: run.updated_at};
        break;
      }
    }
  }
  return {now, reportDate, checkpoint: checkpoint.state, publicReport: reportState,
    deliveryStatus: statusState, activeRun, source, repository: REPO,
    workflow: WORKFLOW};
}

export class RecoveryLedger extends DurableObject {
  constructor(ctx, env) {
    super(ctx, env);
    this.ctx.storage.sql.exec(`CREATE TABLE IF NOT EXISTS attempts (
      report_date TEXT PRIMARY KEY, reason TEXT NOT NULL,
      status TEXT NOT NULL, workflow_run_id INTEGER)`);
    this.ctx.storage.sql.exec(`CREATE TABLE IF NOT EXISTS checks (
      report_date TEXT PRIMARY KEY, status TEXT NOT NULL,
      failure_code TEXT, observed_at TEXT NOT NULL)`);
  }

  async recordFailure(reportDate, failureCode, observedAt) {
    if (!/^\d{4}-\d{2}-\d{2}$/.test(reportDate) ||
        !['github_read_unavailable', 'pages_read_unavailable', 'pages_json_invalid',
          'runs_response_invalid', 'observation_failed'].includes(failureCode)) {
      return {status: 'invalid_failure_record'};
    }
    this.ctx.storage.sql.exec(
      `INSERT INTO checks (report_date, status, failure_code, observed_at)
       VALUES (?, 'failed', ?, ?)
       ON CONFLICT(report_date) DO UPDATE SET status='failed',
       failure_code=excluded.failure_code, observed_at=excluded.observed_at`,
      reportDate, failureCode, observedAt);
    return {status: 'failure_recorded'};
  }

  async attempt(decision) {
    if (decision.action !== 'dispatch' || decision.reason !== 'missing_checkpoint' ||
        !/^\d{4}-\d{2}-\d{2}$/.test(decision.reportDate)) {
      return {status: 'invalid_decision'};
    }
    const claimOnce = async (date, reason) => {
      const result = this.ctx.storage.sql.exec(
        'INSERT OR IGNORE INTO attempts (report_date, reason, status) VALUES (?, ?, ?)',
        date, reason, 'claimed');
      return result.rowsWritten > 0;
    };
    const dispatch = async current => {
      const response = await fetch(`${API}/actions/workflows/daily_market_brief.yml/dispatches`, {
        method: 'POST', headers: {...HEADERS,
          'Authorization': `Bearer ${this.env.GH_ACTIONS_TOKEN}`,
          'Content-Type': 'application/json'},
        body: JSON.stringify({ref: 'main', inputs: {
          morning_recovery_date: current.reportDate,
          morning_recovery_reason: current.reason,
        }}),
      });
      if (!response.ok) throw new Error('dispatch_rejected');
      // Do not log provider body; a run ID is operational metadata only.
      const metadata = await response.json().catch(() => ({}));
      return {workflowRunId: Number.isSafeInteger(metadata.workflow_run_id) ?
        metadata.workflow_run_id : null};
    };
    const result = await executeRecovery(decision, {claimOnce, dispatch}, {dryRun: false});
    if (result.status === 'dispatched' || result.status === 'dispatch_failed') {
      this.ctx.storage.sql.exec('UPDATE attempts SET status = ?, workflow_run_id = ? WHERE report_date = ?',
        result.status, result.workflowRunId ?? null, decision.reportDate);
    }
    return result;
  }
}

export default {
  async scheduled(_controller, env) {
    const now = new Date().toISOString();
    if (!env.GH_ACTIONS_TOKEN || !env.RECOVERY_LEDGER) {
      console.log(JSON.stringify({watchdog_status: 'missing_runtime_configuration'}));
      return;
    }
    try {
      const decision = decideRecovery(await snapshot(now));
      if (decision.action !== 'dispatch') {
        console.log(JSON.stringify({watchdog_status: 'no_action', reason: decision.reason}));
        return;
      }
      const id = env.RECOVERY_LEDGER.idFromName('ai-market-morning');
      const result = await env.RECOVERY_LEDGER.get(id).attempt(decision);
      console.log(JSON.stringify({watchdog_status: result.status, reason: result.reason,
        report_date: result.reportDate, workflow_run_id: result.workflowRunId ?? null}));
    } catch (error) {
      const allowed = new Set(['github_read_unavailable', 'pages_read_unavailable',
        'pages_json_invalid', 'runs_response_invalid']);
      const failureCode = allowed.has(error?.message) ? error.message : 'observation_failed';
      try {
        const id = env.RECOVERY_LEDGER.idFromName('ai-market-morning');
        await env.RECOVERY_LEDGER.get(id).recordFailure(taipeiDate(now), failureCode, now);
      } catch { /* Keep the original normalized failure visible in logs. */ }
      console.log(JSON.stringify({watchdog_status: 'observation_failed',
        failure_code: failureCode}));
    }
  },
};
