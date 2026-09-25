# Phase 15.1 — Morning Report delivery reliability review

Review state: a real 2026-09-25 Morning Report was created, reused and published, but **reliable delivery around 08:30 is not validated**. The scheduled jobs were hours late and the first run's Pages deployment was skipped. Phase 15.2 remains blocked pending review of delivery punctuality and first-run deployment.

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

## 2026-09-25 live validation

| Check | Observed result |
| --- | --- |
| First scheduled run | [36097782655](https://github.com/froyo1015/AI-Market-Intelligence/actions/runs/36097782655), commit `7be0453675600ac876b1bd82f0f386ba50a514cb`, started 05:15:16 UTC / **13:15 Taipei**, not 08:30. |
| Pre-cutoff source | Artifact `10793573984` from run `35965530791`, completed 2026-09-24 06:40:08 UTC, before the 2026-09-25 00:30 UTC baseline cutoff. No post-cutoff source was substituted. |
| Creation | First run logged `created=true`; report `morning_2026-09-25_18dffa5250aa665807fb`, date 2026-09-25, 2 validated Top items, partial data. |
| First publication | `generate` succeeded and uploaded a Pages artifact, but its `Deploy GitHub Pages` job was **skipped**. Thus first-run workflow success was not public delivery. The skipped prerequisite `morning_retry_preflight` appears to propagate through the dependent job graph; this needs a scoped workflow review before claiming first-attempt reliability. |
| Bounded retry | [36100897280](https://github.com/froyo1015/AI-Market-Intelligence/actions/runs/36100897280) started 05:59:50 UTC / **13:59 Taipei**, saw public publication missing, then logged `created=false`, `reused`, creator run `36097782655`. Its Pages deploy job succeeded. |
| Public URL | [Morning Report JSON](https://froyo1015.github.io/AI-Market-Intelligence/data/morning_report_public.json) returned 200. [Delivery status JSON](https://froyo1015.github.io/AI-Market-Intelligence/data/morning_delivery_status.json) reports `reused`, 2026-09-25, retry ordinal 1. |
| Byte integrity | Run A artifact, Run B artifact, `morning-reports` dated checkpoint, public Pages report and status hash all agree on SHA-256 `b0e0ae17c34d0430ac22549f7e6fd4d47d28bfa2e4d0ebbc9b703e956bbb42d8`. Exactly one archive commit touches today's dated path. |
| Intraday changes | Market snapshot hash changed from `e42922674c732e3d7ce4b102f6b50eb9ffc35e0ab31cbc0c034b9b69dd1d54ec` (A) to `43091cfc22629044e1a67cd53d6a4f94015fddc313f874b999f866df3fdc74fa` (B); BTC, ETH and Gold prices also changed. Morning report bytes did not. B therefore demonstrates both same-day reuse and immunity to new intraday inputs. No separate third run was performed. |
| Security | Public report passed `validate_public`; public JSON scan found no API-key pattern, local path, Authorization header, raw provider response or internal path. |

This is real creation, immutability and eventual publication—not a punctual 08:30 delivery guarantee. The 08:30 and 09:06 cron invocations were approximately 4 hours 45 minutes late. The first run's skipped deployment is an additional workflow-level defect. Do not call Phase 15.1 fully ready or enter Phase 15.2 without reviewing these limits. Next-day rollover is covered by deterministic tests only; no live next-day claim is made.
