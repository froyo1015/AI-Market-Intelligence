import assert from 'node:assert/strict';
import {test} from 'node:test';
import {execFileSync} from 'node:child_process';
import {readFileSync} from 'node:fs';
import {decideReference, executeReference, verifyReferenceCheckpoint}
  from '../../src/daily_reference/watchdog_core.mjs';
import {sha256} from '../../src/morning_report/watchdog_core.mjs';

const day = '2026-09-23', now = `${day}T00:03:00Z`;
const decision = (slot = 3) => ({...decideReference({now, referenceDate: day, checkpoint: 'missing'}), slot});

test('legal missing dispatch, valid checkpoint no-op, closed windows and invalid state', () => {
  assert.equal(decision().action, 'dispatch');
  for (const checkpoint of ['valid', 'invalid', 'unavailable'])
    assert.equal(decideReference({now, referenceDate: day, checkpoint}).action, 'no_action');
  for (const instant of [`${day}T00:30:00.001Z`, '2026-09-22T23:59:59Z'])
    assert.equal(decideReference({now: instant, referenceDate: day, checkpoint: 'missing'}).action, 'no_action');
  assert.equal(decideReference({now: `${day}T00:30:00Z`, referenceDate: day, checkpoint: 'missing'}).action, 'dispatch');
});

test('repeated/concurrent cron has only one active attempt', async () => {
  for (const fails of [false, true]) {
    const claimed = new Set(); let calls = 0;
    const deps = {clock: () => now, claimAttempt: async date => {
      if (claimed.has(date)) return false; claimed.add(date); return true;
    }, dispatch: async () => {calls++; if (fails) throw new Error('dispatch_rejected'); return {workflowRunId: 123};}};
    const results = await Promise.all(Array.from({length: 3}, () => executeReference(decision(), deps)));
    assert.equal(calls, 1);
    assert.equal(results.filter(r => r.status === 'already_attempted').length, 2);
    assert.ok(!JSON.stringify(results).includes('TOKEN'));
  }
});

test('lookup/claim delay across cutoff never dispatches', async () => {
  let calls = 0, ticks = 0;
  const result = await executeReference(decision(), {clock: () => ++ticks === 1 ? now : `${day}T00:30:01Z`,
    claimAttempt: async () => true, dispatch: async () => {calls++;}});
  assert.equal(result.reason, 'capture_after_cutoff'); assert.equal(calls, 0);
});

test('failure at 08:03 retries at 08:13, success locks out 08:23 and same-slot replay', async () => {
  let state = null, instant = now, calls = 0;
  const deps = {clock: () => instant, claimAttempt: async (_day, slot) => {
    if (state && !(state.status === 'dispatch_failed' && state.slot < slot)) return false;
    state = {status: 'claimed', slot}; return true;
  }, dispatch: async () => {if (++calls === 1) throw new Error('dispatch_rejected'); return {workflowRunId: 222};}};
  async function attempt(slot) {
    const result = await executeReference(decision(slot), deps);
    if (['dispatched', 'dispatch_failed', 'dispatch_unknown'].includes(result.status)) state.status = result.status;
    return result;
  }
  assert.equal((await attempt(3)).status, 'dispatch_failed');
  assert.equal((await attempt(3)).status, 'already_attempted');
  instant = `${day}T00:13:00Z`;
  assert.equal((await attempt(13)).status, 'dispatched');
  instant = `${day}T00:23:00Z`;
  assert.equal((await attempt(23)).status, 'already_attempted');
  assert.equal(calls, 2);
});

test('successful first dispatch stops later slots; retry after cutoff never claims', async () => {
  let calls = 0, claims = 0, claimed = false, instant = now;
  const deps = {clock: () => instant, claimAttempt: async () => {
    claims++; if (claimed) return false; claimed = true; return true;
  }, dispatch: async () => {calls++; return {workflowRunId: null};}};
  assert.equal((await executeReference(decision(3), deps)).status, 'dispatched');
  for (const slot of [13,23]) assert.equal((await executeReference(decision(slot),deps)).status, 'already_attempted');
  assert.equal(calls, 1);
  instant = `${day}T00:30:01Z`; const before = claims;
  assert.equal((await executeReference(decision(23),deps)).reason, 'capture_after_cutoff');
  assert.equal(claims, before);
});

test('lost response is normalized unknown rather than a definite rejection', async () => {
  const result = await executeReference(decision(), {clock: () => now, claimAttempt: async () => true,
    dispatch: async () => {throw new Error('PRIVATE network response');}});
  assert.deepEqual(result, {status:'dispatch_unknown',reason:'dispatch_outcome_unknown'});
});

test('Python-validated canonical fixture requires hash, history and creator identity', async () => {
  const raw = execFileSync('.venv/bin/python', ['-c',
    "import runpy; from src.daily_reference.checkpoint import build_capture; from src.daily_reference.model import canonical_bytes; t=runpy.run_path('tests/test_daily_market_reference.py'); print(canonical_bytes(build_capture(t['collect'](now=t['NOW'],fetcher=t['feeds']), captured_at='2026-09-23T00:10:00Z')).decode(),end='')"]);
  const digest = await sha256(raw), head = 'a'.repeat(40);
  const record = {path: `2026/${day}/daily_reference_capture_public.json`, type: 'file', encoding: 'base64', content: raw.toString('base64')};
  const workflow = '.github/workflows/daily_reference_capture.yml';
  const repo = 'froyo1015/AI-Market-Intelligence';
  const message = ['daily-reference-checkpoint:v1','capture',day,repo,'main',workflow,'123',head,digest].join('|');
  const run = {id:123,path:workflow,head_branch:'main',head_sha:head,repository:{full_name:repo},head_repository:{full_name:repo}};
  const get = async path => path.startsWith('/commits?') ? [{commit:{message}}] : run;
  assert.equal((await verifyReferenceCheckpoint(record, day, get)).state, 'valid');
  assert.equal((await verifyReferenceCheckpoint(null, day, async () => [])).state, 'missing');
  assert.equal((await verifyReferenceCheckpoint(null, day, get)).state, 'invalid'); // removed
  for (const mutate of [r => ({...r,head_sha:'b'.repeat(40)}),r => ({...r,path:'.github/workflows/other.yml'}),r => ({...r,head_branch:'other'})])
    assert.equal((await verifyReferenceCheckpoint(record, day, async path => path.startsWith('/commits?') ? [{commit:{message}}] : mutate(run))).state, 'invalid');
  assert.equal((await verifyReferenceCheckpoint({...record,content:Buffer.from('{}').toString('base64')},day,get)).state,'invalid');
  assert.equal((await verifyReferenceCheckpoint(record,day,async () => [{commit:{message:message+'x'}}])).state,'invalid');
  await assert.rejects(verifyReferenceCheckpoint(record,day,async () => {throw new Error('read_failed');}));
});

test('actual Worker routes reference Cron, uses isolated SQL claim and safe dispatch/logging', async () => {
  const originalDate = globalThis.Date, originalFetch = globalThis.fetch, originalLog = console.log;
  const writes = new Map(), logs = [], requests = [];
  let instant = now, failPost = false, holdPost = null;
  globalThis.Date = class extends originalDate {constructor(...args) {super(...(args.length ? args : [instant]));}};
  globalThis.__ReferenceTestDO = class {constructor(ctx, env) {this.ctx=ctx;this.env=env;}};
  let source = readFileSync(new URL('../../watchdog/morning_worker.mjs',import.meta.url),'utf8');
  source = source.replace("import {DurableObject} from 'cloudflare:workers';", 'const DurableObject = globalThis.__ReferenceTestDO;')
    .replace("'../src/morning_report/watchdog_core.mjs'", JSON.stringify(new URL('../../src/morning_report/watchdog_core.mjs',import.meta.url).href))
    .replace("'../src/daily_reference/watchdog_core.mjs'", JSON.stringify(new URL('../../src/daily_reference/watchdog_core.mjs',import.meta.url).href));
  try {
    const {default: worker, RecoveryLedger} = await import(`data:text/javascript;base64,${Buffer.from(source).toString('base64')}`);
    const ledger = new RecoveryLedger({storage:{sql:{exec(sql,...args) {
      if (sql.startsWith('INSERT INTO reference_attempts')) {
        const prior = writes.get(args[0]);
        if (prior && !(prior.status==='dispatch_failed' && prior.slot < args[2])) return {rowsWritten:0};
        writes.set(args[0],{status:'claimed',slot:args[2]}); return {rowsWritten:1};
      }
      if (sql.startsWith('UPDATE reference_attempts')) {
        const prior = writes.get(args[2]);
        if (prior?.status==='claimed' && prior.slot===args[3]) prior.status=args[0];
      }
      return {rowsWritten:0};
    }}}}, {GH_ACTIONS_TOKEN:'SECRET_TEST_ONLY'});
    const names=[];
    const env={GH_ACTIONS_TOKEN:'SECRET_TEST_ONLY',RECOVERY_LEDGER:{idFromName(name){names.push(name);return name;},get(){return ledger;}}};
    globalThis.fetch = async (url,options={}) => {
      requests.push({url,method:options.method??'GET',body:options.body});
      if (options.method==='POST') {
        if (holdPost) await holdPost;
        return new Response(null,{status:failPost ? 503 : 204});
      }
      if (url.includes('/git/ref/')) return Response.json({ref:'refs/heads/morning-reports'});
      if (url.includes('/contents/')) return new Response(null,{status:404});
      if (url.includes('/commits?')) return Response.json([]);
      throw new Error('PRIVATE transport text');
    };
    console.log = line => logs.push(JSON.parse(line));
    for (const cron of ['3 0 * * *','13 0 * * *','23 0 * * *']) await worker.scheduled({cron},env);
    assert.equal(requests.filter(r=>r.method==='POST').length,1);
    assert.equal(writes.get(day).status,'dispatched'); // duplicate check cannot overwrite success
    assert.ok(names.every(name=>name==='ai-market-daily-reference'));
    const post=requests.find(r=>r.method==='POST');
    assert.ok(post.url.endsWith('/daily_reference_capture.yml/dispatches'));
    assert.deepEqual(JSON.parse(post.body),{ref:'main'});
    assert.ok(!requests.some(r=>r.method==='PUT')); // checkpoint writes remain Python-only
    assert.ok(logs.every(l=>Object.keys(l).sort().join() === ['subsystem','status','reason_code','reference_date','workflow_run_id','timestamp'].sort().join()));
    assert.ok(!JSON.stringify(logs).includes('SECRET'));

    writes.clear(); requests.length=0; failPost=true;
    await worker.scheduled({cron:'3 0 * * *'},env);
    assert.equal(writes.get(day).status,'dispatch_failed');
    await worker.scheduled({cron:'3 0 * * *'},env); // same-slot replay cannot retry
    assert.equal(requests.filter(r=>r.method==='POST').length,1);
    failPost=false; instant=`${day}T00:13:00Z`;
    await worker.scheduled({cron:'13 0 * * *'},env);
    assert.equal(writes.get(day).status,'dispatched');
    instant=`${day}T00:23:00Z`;
    await worker.scheduled({cron:'23 0 * * *'},env);
    assert.equal(requests.filter(r=>r.method==='POST').length,2);

    writes.clear(); requests.length=0; instant=now;
    let release; holdPost=new Promise(resolve=>{release=resolve;});
    const first=worker.scheduled({cron:'3 0 * * *'},env);
    // Wait until first POST is active, then deliver another invocation.
    while (!requests.some(r=>r.method==='POST')) await new Promise(resolve=>setImmediate(resolve));
    await worker.scheduled({cron:'13 0 * * *'},env);
    assert.equal(requests.filter(r=>r.method==='POST').length,1);
    release(); await first; holdPost=null;
    assert.equal(writes.get(day).status,'dispatched');

    writes.clear(); requests.length=0; instant=now; failPost=true;
    await worker.scheduled({cron:'3 0 * * *'},env);
    instant=`${day}T00:30:01Z`;
    await worker.scheduled({cron:'13 0 * * *'},env);
    assert.equal(requests.filter(r=>r.method==='POST').length,1);
    assert.equal(writes.get(day).status,'dispatch_failed');
    requests.length=0;
    await worker.scheduled({cron:'55 0 * * *'},env);
    assert.ok(requests.some(r=>r.url.includes('morning_report_public.json')));
    assert.ok(!requests.some(r=>r.url.includes('daily_reference_capture_public.json')));
  } finally {globalThis.Date=originalDate;globalThis.fetch=originalFetch;console.log=originalLog;delete globalThis.__ReferenceTestDO;}
});
