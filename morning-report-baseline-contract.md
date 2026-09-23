# Phase 13.2 — Fixed Morning Report baseline contract

## Purpose and identity

`morning_report.json` records one fixed, evidence-backed baseline for a local Taiwan calendar date. `report_type="morning"`, `baseline_for_date=report_date`, `timezone="Asia/Taipei"`, `baseline_timestamp=08:30` local expressed in UTC, `generated_at` is the actual successful generation time, and `source_run_id` is the existing orchestration manifest run. `version="morning_report_v1"` and `immutable_for_day=true` are required. Report date is a local date, not the source intelligence artifact's reporting date; previous-day validated output may be used, with its actual time and freshness preserved.

The scheduled morning cutoff is **08:30 Asia/Taipei**. The existing Actions schedule already uses `cron: "30 8 * * *"` plus `timezone: "Asia/Taipei"`; GitHub supports this timezone form. Its UTC equivalent is 00:30 year-round because Taipei has no DST. A late workflow execution is assigned to its intended local date and retains both the scheduled cutoff and actual generation timestamp. A run after that local day ends does not silently backfill it. This phase leaves the existing workflow unchanged.

## Source and content contract

Inputs: existing validated `daily_intelligence.json`, linked `top_intelligence.json`, and same-run `run_manifest.json`. The manifest's SHA-256 entries must match the two input bytes. Their generated timestamps must be on or before the scheduled cutoff. The source intelligence report date may be the target local day or previous local day only. Invalid linkage, future data or stale inputs fail closed. No macro calendar, earnings, derivative, AI, Market Pulse, prediction or ranking input is required.

Content is a deterministic Chinese presentation of validated structured facts:

1. 今日市場一句話 — current validated regime where available, otherwise an explicit evidence limitation.
2. 隔夜市場重點 — only selected current items with observation timestamps in the previous 18:00–08:30 Taipei interval; otherwise explicit insufficient evidence. A timestamped scheduled event does not count as an observed overnight fact.
3. 今日最重要 2–3 件事 — existing Top Intelligence rank order, at most three. Past scheduled events are excluded from today's watch list. Fewer eligible items remain fewer; none are invented.
4. 市場環境 — current validated classification or explicit unavailable state.
5. 已知限制 — existing partial/stale/unavailable status remains visible.
6. Evidence — every included item keeps its item ID, source IDs, evidence references and timestamps in the private baseline and safe public projection.

The writer uses type-specific Chinese templates. It never uses raw machine headlines as public prose, infers a new market cause, or changes source ranking. Rising prices do not become recommendations; risk-off is a current classification, not a forecast. Existing source times and validation states remain in the artifact, while user copy is concise.

## Immutability and failure behavior

One archive path per local report date: `YYYY/YYYY-MM-DD/morning_report.json`, plus a same-date public projection. A validated baseline is linked into the path only when absent; later retries return its original bytes and source run, regardless of newly generated intelligence. Two concurrent writers race on atomic create-only insertion; one wins, the other loads the winner. The public projection is derived from the stored winner and also created once. Corrupt or conflicting existing files stop the run rather than being overwritten.

If input validation or the first run fails before insertion, no baseline is created. A later same-day recovery attempt may create it. If the private baseline succeeds but public projection creation fails, retry regenerates the projection from that private baseline without rebuilding it. At next local date a separate path is used. `baseline_timestamp` remains the scheduled cutoff even when actual generation is delayed.

The local archive proves process-level idempotence and restart/retrieval behavior. GitHub-hosted durability needs the separately reviewed persistence integration described in `morning-report-persistence-review.md`. No production deployment is claimed at this stage.

## Public contract

`morning_report_public.json` contains report identity, Chinese content, source names, timestamp, status/freshness/limitations and evidence IDs. It excludes filesystem paths, debug data, raw responses, prompts, credentials and hidden fields. `report_type="morning"` and `baseline_for_date` let a future frontend distinguish it from a later latest/pulse artifact. The sample files under `samples/` are historical replay artifacts and explicitly marked `sample_only`.

The sample replays the September 3 validated source run at a **simulated September 4, 2026 08:30 Taiwan cutoff**, with a simulated 08:32 completion. It is contract evidence, not a claim that this Morning Report ran in production on that date.
