/** Deterministic, provider-neutral Morning recovery decision boundary. */
const WINDOW_START = '00:45:00Z'; // 08:45 Asia/Taipei
const WINDOW_END = '01:30:00Z';   // 09:30 Asia/Taipei
const REPO = 'froyo1015/AI-Market-Intelligence';
const WORKFLOW = '.github/workflows/daily_market_brief.yml';

export async function sha256(bytes) {
  const digest = await crypto.subtle.digest('SHA-256', bytes);
  return [...new Uint8Array(digest)].map(byte => byte.toString(16).padStart(2, '0')).join('');
}

/** Validate the dated archive and its create-only GitHub provenance, not JSON shape alone. */
export async function verifyCanonicalCheckpoint(record, reportDate, getJson) {
  if (record === null) return {state: 'missing', report: null, digest: null};
  const path = `${reportDate.slice(0, 4)}/${reportDate}/morning_report_public.json`;
  if (record?.path !== path || record?.type !== 'file' ||
      record?.encoding !== 'base64' || typeof record?.content !== 'string') {
    return {state: 'invalid', report: null, digest: null};
  }
  let report, bytes;
  try {
    bytes = Uint8Array.from(atob(record.content.replace(/\s/g, '')),
      char => char.charCodeAt(0));
    if (!bytes.length || bytes.length > 256_000) throw new Error('invalid_size');
    report = JSON.parse(new TextDecoder('utf-8', {fatal: true}).decode(bytes));
    const required = ['version', 'report_type', 'baseline_for_date', 'generated_at',
      'baseline_timestamp', 'timezone', 'report_id', 'data_status', 'freshness_status',
      'source_run_id', 'source_artifact_refs', 'source_report_date',
      'immutable_for_day', 'sample_only', 'content'];
    if (!report || Object.keys(report).sort().join() !== required.sort().join() ||
        report.version !== 'morning_report_v1' || report.report_type !== 'morning' ||
        report.baseline_for_date !== reportDate || report.timezone !== 'Asia/Taipei' ||
        report.sample_only !== false || report.immutable_for_day !== true ||
        !['available', 'partial'].includes(report.data_status) ||
        !['current', 'stale'].includes(report.freshness_status) ||
        typeof report.report_id !== 'string' ||
        !report.report_id.startsWith(`morning_${reportDate}_`) ||
        !Number.isSafeInteger(report.source_run_id) ||
        !Array.isArray(report.source_artifact_refs) || !report.source_artifact_refs.length ||
        report.source_artifact_refs.some(ref =>
          !['daily_intelligence.json', 'top_intelligence.json'].includes(ref?.artifact) ||
          !/^[a-f0-9]{64}$/.test(ref?.sha256)) ||
        !report.content || !Array.isArray(report.content.top_items) ||
        report.content.top_items.length > 3 ||
        !Array.isArray(report.content.overnight_highlights) ||
        report.content.overnight_highlights.length > 3) throw new Error('invalid_contract');
    const baseline = Date.parse(report.baseline_timestamp);
    const generated = Date.parse(report.generated_at);
    if (!Number.isFinite(baseline) ||
        !Number.isFinite(generated) ||
        baseline !== Date.parse(`${reportDate}T00:30:00Z`) ||
        generated < baseline) throw new Error('invalid_pit');
  } catch { return {state: 'invalid', report: null, digest: null}; }
  const digest = await sha256(bytes);
  const commits = await getJson(`/commits?sha=morning-reports&path=${encodeURIComponent(path)}&per_page=2`);
  if (!Array.isArray(commits) || commits.length !== 1) {
    return {state: 'invalid', report: null, digest: null};
  }
  const parts = commits[0]?.commit?.message?.split('|') || [];
  if (parts.length !== 8 || parts[0] !== 'morning-checkpoint:v1' ||
      parts[1] !== reportDate || parts[2] !== REPO || parts[3] !== 'main' ||
      parts[4] !== WORKFLOW || !/^\d+$/.test(parts[5]) ||
      !/^[a-f0-9]{40}$/.test(parts[6]) || parts[7] !== digest) {
    return {state: 'invalid', report: null, digest: null};
  }
  const creatorRun = await getJson(`/actions/runs/${parts[5]}`);
  if (creatorRun?.id !== Number(parts[5]) || creatorRun.path !== WORKFLOW ||
      creatorRun.head_branch !== 'main' || creatorRun.head_sha !== parts[6] ||
      creatorRun.head_repository?.full_name !== REPO ||
      creatorRun.repository?.full_name !== REPO) {
    return {state: 'invalid', report: null, digest: null};
  }
  return {state: 'valid', report, digest};
}

export function taipeiDate(now) {
  const instant = new Date(now);
  if (!Number.isFinite(instant.getTime())) throw new Error('invalid_watchdog_time');
  return new Date(instant.getTime() + 8 * 3600_000).toISOString().slice(0, 10);
}

export function decideRecovery(snapshot) {
  const {now, reportDate, checkpoint, publicReport, deliveryStatus, activeRun,
    source, repository, workflow} = snapshot;
  const date = taipeiDate(now);
  if (reportDate !== date || !/^\d{4}-\d{2}-\d{2}$/.test(reportDate)) {
    return {action: 'no_action', reason: 'wrong_report_date'};
  }
  const instant = new Date(now).getTime();
  const start = Date.parse(`${date}T${WINDOW_START}`);
  const end = Date.parse(`${date}T${WINDOW_END}`);
  if (instant < start || instant > end) {
    return {action: 'no_action', reason: 'outside_recovery_window'};
  }
  if (checkpoint === 'invalid') {
    return {action: 'no_action', reason: 'checkpoint_invalid'};
  }
  if (checkpoint === 'valid') {
    return {action: 'no_action', reason: publicReport === 'matching' &&
      deliveryStatus === 'matching' ? 'already_delivered' : 'checkpoint_exists_public_unconfirmed'};
  }
  if (checkpoint !== 'missing' || !['missing', 'prior_day'].includes(publicReport)) {
    return {action: 'no_action', reason: 'inconsistent_public_state'};
  }
  if (activeRun) return {action: 'no_action', reason: 'workflow_active'};
  const cutoff = Date.parse(`${date}T00:30:00Z`);
  const sourceTime = Date.parse(source?.completedAt ?? '');
  if (!source || source.repository !== repository || source.workflow !== workflow ||
      source.branch !== 'main' || source.status !== 'success' ||
      !Number.isSafeInteger(source.runId) || !Number.isSafeInteger(source.artifactId) ||
      !Number.isFinite(sourceTime) || sourceTime > cutoff || sourceTime >= instant) {
    return {action: 'no_action', reason: 'no_verified_pre_cutoff_source'};
  }
  return {action: 'dispatch', reason: 'missing_checkpoint', reportDate: date,
    sourceRunId: source.runId, sourceArtifactId: source.artifactId};
}

/** claimOnce must be a durable, atomic per-date operation in production. */
export async function executeRecovery(decision, {claimOnce, dispatch}, {dryRun = true} = {}) {
  if (decision.action !== 'dispatch') return {status: 'no_action', reason: decision.reason};
  if (dryRun) return {status: 'would_dispatch', reason: decision.reason,
    reportDate: decision.reportDate};
  if (!await claimOnce(decision.reportDate, decision.reason)) {
    return {status: 'already_attempted', reason: decision.reason,
      reportDate: decision.reportDate};
  }
  try {
    const run = await dispatch(decision);
    return {status: 'dispatched', reason: decision.reason, reportDate: decision.reportDate,
      workflowRunId: run.workflowRunId};
  } catch {
    // The claim remains: one attempt only, never an unbounded dispatch retry.
    return {status: 'dispatch_failed', reason: decision.reason,
      reportDate: decision.reportDate};
  }
}
