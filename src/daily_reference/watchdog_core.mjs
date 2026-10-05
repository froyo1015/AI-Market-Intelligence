/** Read-only checkpoint provenance and bounded external capture dispatch. */
import {sha256, taipeiDate} from '../morning_report/watchdog_core.mjs';

export const REFERENCE_WORKFLOW = '.github/workflows/daily_reference_capture.yml';
const REPO = 'froyo1015/AI-Market-Intelligence';
const keys = (object, expected) => object && !Array.isArray(object) &&
  Object.keys(object).sort().join() === [...expected].sort().join();
function canonical(value) {
  if (Array.isArray(value)) return `[${value.map(canonical).join(',')}]`;
  if (value && typeof value === 'object') return `{${Object.keys(value).sort()
    .map(key => `${JSON.stringify(key)}:${canonical(value[key])}`).join(',')}}`;
  return JSON.stringify(value);
}

/** A digest alone or a basic JSON shape is never canonical provenance. */
export async function verifyReferenceCheckpoint(record, day, getJson) {
  const invalid = {state: 'invalid'};
  const path = `${day.slice(0, 4)}/${day}/daily_reference_capture_public.json`;
  // A removed checkpoint must not be mistaken for a fresh missing day.
  const commits = await getJson(`/commits?sha=morning-reports&path=${encodeURIComponent(path)}&per_page=2`);
  if (!Array.isArray(commits)) return invalid;
  if (record === null) return commits.length === 0 ? {state: 'missing'} : invalid;
  if (commits.length !== 1 || record?.path !== path || record.type !== 'file' ||
      record.encoding !== 'base64' || typeof record.content !== 'string') return invalid;
  let bytes, payload;
  try {
    bytes = Uint8Array.from(atob(record.content.replace(/\s/g, '')), c => c.charCodeAt(0));
    if (!bytes.length || bytes.length > 96_000) return invalid;
    const text = new TextDecoder('utf-8', {fatal: true}).decode(bytes);
    payload = JSON.parse(text);
    if (text !== canonical(payload) + '\n' || !keys(payload,
      ['version', 'report_date', 'timezone', 'captured_at', 'reference_sha256', 'reference']) ||
      payload.version !== 'daily_reference_capture_v1' || payload.report_date !== day ||
      payload.timezone !== 'Asia/Taipei') return invalid;
    const captured = Date.parse(payload.captured_at);
    const generated = Date.parse(payload.reference?.generated_at);
    if (!Number.isFinite(captured) || !Number.isFinite(generated) || generated > captured ||
        captured > Date.parse(`${day}T00:30:00Z`) || taipeiDate(payload.captured_at) !== day ||
        !keys(payload.reference, ['version', 'reference_kind', 'generated_at', 'status', 'assets']) ||
        payload.reference.version !== 'daily_market_reference_v1' ||
        payload.reference.reference_kind !== 'official_daily_reference' ||
        !['available', 'partial'].includes(payload.reference.status) ||
        !Array.isArray(payload.reference.assets) ||
        payload.reference.assets.map(a => a?.asset_id).join() !== 'US10Y,EURUSD,USDJPY,GBPUSD' ||
        !/^[a-f0-9]{64}$/.test(payload.reference_sha256)) return invalid;
    if (await sha256(new TextEncoder().encode(canonical(payload.reference) + '\n')) !==
        payload.reference_sha256) return invalid;
  } catch { return invalid; }
  const digest = await sha256(bytes);
  const parts = commits[0]?.commit?.message?.split('|') || [];
  if (parts.length !== 9 || parts[0] !== 'daily-reference-checkpoint:v1' ||
      parts[1] !== 'capture' || parts[2] !== day || parts[3] !== REPO ||
      parts[4] !== 'main' || parts[5] !== REFERENCE_WORKFLOW ||
      !/^\d+$/.test(parts[6]) || !Number.isSafeInteger(Number(parts[6])) ||
      !/^[a-f0-9]{40}$/.test(parts[7]) || parts[8] !== digest) return invalid;
  const run = await getJson(`/actions/runs/${parts[6]}`);
  if (run?.id !== Number(parts[6]) || run.path !== REFERENCE_WORKFLOW ||
      run.head_branch !== 'main' || run.head_sha !== parts[7] ||
      run.repository?.full_name !== REPO || run.head_repository?.full_name !== REPO) return invalid;
  return {state: 'valid', creatorRunId: run.id, digest};
}

export function decideReference({now, referenceDate, checkpoint}) {
  let day;
  try { day = taipeiDate(now); } catch { return {action: 'no_action', reason: 'invalid_time'}; }
  const base = {referenceDate: day};
  if (referenceDate !== day) return {...base, action: 'no_action', reason: 'wrong_reference_date'};
  if (checkpoint === 'valid') return {...base, action: 'no_action', reason: 'checkpoint_exists'};
  if (checkpoint !== 'missing') return {...base, action: 'no_action', reason: 'checkpoint_invalid'};
  const time = Date.parse(now);
  if (time < Date.parse(`${day}T00:00:00Z`))
    return {...base, action: 'no_action', reason: 'capture_window_not_open'};
  if (time > Date.parse(`${day}T00:30:00Z`))
    return {...base, action: 'no_action', reason: 'capture_after_cutoff'};
  return {...base, action: 'dispatch', reason: 'missing_checkpoint'};
}

export async function executeReference(decision, {claimAttempt, dispatch, clock}) {
  if (decision.action !== 'dispatch') return {status: 'no_action', reason: decision.reason};
  if (![3, 13, 23].includes(decision.slot)) return {status: 'no_action', reason: 'invalid_slot'};
  const inWindow = () => decideReference({now: clock(), referenceDate: decision.referenceDate,
    checkpoint: 'missing'});
  let checked = inWindow();
  if (checked.action !== 'dispatch') return {status: 'no_action', reason: checked.reason};
  if (!await claimAttempt(decision.referenceDate, decision.slot))
    return {status: 'already_attempted', reason: 'claim_exists'};
  checked = inWindow();
  if (checked.action !== 'dispatch') return {status: 'no_action', reason: checked.reason};
  try {
    const result = await dispatch();
    return {status: 'dispatched', reason: 'missing_checkpoint', workflowRunId: result.workflowRunId ?? null};
  } catch (error) {
    // A received rejection may retry next slot; a lost response is not proof of failure.
    return error?.message === 'dispatch_rejected' ?
      {status: 'dispatch_failed', reason: 'dispatch_rejected'} :
      {status: 'dispatch_unknown', reason: 'dispatch_outcome_unknown'};
  }
}
