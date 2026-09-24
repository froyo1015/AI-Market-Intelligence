# Phase 15.1 — Morning Report delivery reliability review

Review state: implementation candidate validated locally; live production delivery **not yet validated**. Do not call the Morning Report reliably delivered until the live checks below pass.

## Failure trace for 2026-09-24

| Stage | Observed result |
| --- | --- |
| Scheduled trigger | [Run 35958991007](https://github.com/froyo1015/AI-Market-Intelligence/actions/runs/35958991007) started 2026-09-24 05:13:26 UTC (13:13 Taipei), after the 08:30 target. |
| Pre-cutoff source | Run 35832903568 was selected; it completed before the 2026-09-24 00:30 UTC cutoff. |
| Source readiness | Aggregate daily/Top source timestamp was 2026-09-21 04:00 UTC, beyond its 48-hour threshold. Two individually validated Top items were still within their own 48-hour windows at the fixed cutoff. |
| Baseline/composer | Old all-or-nothing aggregate freshness check marked the entire Morning candidate unavailable. |
| Checkpoint | `source_unavailable_no_checkpoint`; no 2026-09-24 dated canonical checkpoint. |
| Public projection | `morning_report_public.json` absent; public request returned 404. |
| Pages | Deployed successfully because the Morning step was allowed to fail. Deployment success therefore did not mean Morning delivery success. |

The candidate change reevaluates selected items at the original 08:30 cutoff using their existing freshness contracts. It does **not** relabel an aged aggregate or stale item as current. A fixed-input replay of the 9/24 pre-cutoff artifact produces a **partial** report with two current market items and the stale-aggregate warning. This replay was not retroactively published as a production Morning Report.

## Candidate delivery behavior

- 08:30 scheduled attempt; one 09:06 scheduled retry. A retry is skipped when the canonical checkpoint and deployed public report already match. It does not make an extra LLM request.
- The first valid dated create-only checkpoint is canonical. Same-day later executions restore its exact public bytes, even after intraday source changes. A new Taipei date gets a separate key.
- The Morning minimum gate requires two current validated non-data-quality Top items, two distinct related assets, one cross-asset-backed item, valid pre-cutoff source manifest/provenance, and no future leakage. Missing optional calendar/reference data cannot by itself veto a useful report.
- If source quality is insufficient, publish a normalized `pending_source` or `unavailable` delivery status without a Morning report. If checkpoint trust fails, fail the Pages build to protect the prior deployment; the failure remains in Actions logs.
- `docs/data/morning_delivery_status.json` is public-safe and independent from the intraday intelligence status. It makes a missing Morning Report observable; it does not claim unavailable content is delivered.

## Validation completed before live activation

- Full Python suite: passed locally; one existing environment-dependent GnuPG skip. See the final test count in the release validation record.
- Focused Morning baseline/checkpoint/delivery tests: 37 passed.
- Fixed 9/24 replay: partial report, two valid Top items, original stale warning retained. Public projection SHA-256: `212921a8098f4841dc3a533f1540adb24164e7c3cd8c874ec49eb0b1fd872cc2` (offline replay only).
- Workflow YAML parse, diff check, public-safe status validation and scoped security checks must pass before commit/push.

## Live acceptance still required

1. Observe a fresh production run in the correct Taipei morning window; record the creation run, source run, canonical checkpoint path, report ID, and public SHA-256.
2. Confirm the public report and delivery status are served by Pages, dated correctly, and byte-identical to the canonical checkpoint.
3. Run the workflow again the same day and confirm `reused`, identical report ID/body/hash, and no second dated archive entry.
4. After upstream data changes, run again and confirm the same canonical report remains. The updated intraday report may change, but the Morning Report may not.
5. Confirm next-day rollover with deterministic tests; a true next-day live claim needs a later actual run.

GitHub cron timing and source availability remain external limits. A successful workflow or Pages deployment alone is insufficient proof of Morning delivery. If the next morning source is unavailable, the correct outcome is explicit non-delivery, not a fabricated report.
