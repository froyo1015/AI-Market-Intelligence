# Public Morning delivery status schema

Artifact: `docs/data/morning_delivery_status.json` → `/data/morning_delivery_status.json` on Pages. Schema version `morning_delivery_v1`. A validated status is produced on every valid Morning workflow attempt. Its date uses Asia/Taipei and is independent from UTC workflow date.

```json
{
  "schema_version": "morning_delivery_v1",
  "report_date": "2026-09-25",
  "status": "reused",
  "report_id": "morning_2026-09-25_<digest>",
  "created_at": "2026-09-25T00:32:00Z",
  "last_attempt_at": "2026-09-25T00:54:30Z",
  "retry_count": 1,
  "reused": true,
  "public_artifact_available": true,
  "failure_code": null,
  "source_readiness_summary": {
    "state": "ready",
    "eligible_top_items": 2,
    "source_report_date": "2026-09-24",
    "source_freshness_status": "stale"
  },
  "source_run_id": "<validated-run-id>",
  "public_artifact_sha256": "<sha256-of-canonical-public-report>"
}
```

`created` and `reused` require a validated same-date public JSON. `created_at` is immutable report generation time; `last_attempt_at` is this workflow attempt time. `public_artifact_sha256` hashes the canonical report projection, never the mutable delivery status. `source_freshness_status=stale` can coexist with an eligible report if only an unrelated aggregate constituent is stale; the report itself remains `partial` and carries the warning.

For `pending_source`, `failed`, or `unavailable`, `report_id`, `created_at`, `source_run_id` and hash are null; `public_artifact_available=false`; `source_readiness_summary.state=not_ready`; and `failure_code` is from a closed normalized allowlist. No provider response, token, headers, local path or raw evidence enters this public status.

State transitions for one date: `pending_source → created → reused`; `failed` may be retried after correcting a trust/transport failure without changing an existing valid checkpoint; final scheduled lack of source yields `unavailable`. A later manual recovery may create the first valid checkpoint from data known before 08:30, but may never rewrite an existing one. Tomorrow starts a new independent date. `retry_count` is the scheduled slot ordinal 0 or 1, not an accumulated GitHub run count.

The JSON is an operational artifact. `status=unavailable` means the Morning Report is unavailable, even when the main market intelligence page and its own Minimum Useful Gate report useful.
