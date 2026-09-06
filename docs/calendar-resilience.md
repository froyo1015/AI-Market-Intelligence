# Phase 7.1-C Resilient Economic Calendar Adapter

## Purpose

The calendar pipeline must remain useful when the BLS iCalendar endpoint returns
HTTP 403 without weakening the Evidence-first boundary. Resilience means using a
second official representation, retaining each source attempt, and refusing to
invent or silently reconcile release times.

This phase changes calendar ingestion and provenance only. It does not change
event impact rules, Intelligence logic, the Risk Monitor, UI, LLM, Telegram, or
trading behavior.

## Approved sources

### Priority 1: primary

| Field | Value |
| --- | --- |
| Source | `bls_release_calendar` |
| Publisher | U.S. Bureau of Labor Statistics |
| Endpoint | `https://www.bls.gov/schedule/news_release/bls.ics` |
| Format | iCalendar (`VEVENT`) |
| Quality | Tier 1 official publisher |

The existing adapter and bounded ICS parser remain authoritative.

### Priority 2: fallback

| Field | Value |
| --- | --- |
| Source | `bea_release_schedule` |
| Publisher | U.S. Bureau of Economic Analysis |
| Endpoint | `https://www.bea.gov/news/schedule/full` |
| Format | Official HTML release table |
| Quality | Tier 1 independent U.S. government publisher |

The fallback is acceptable because BEA is the official publisher for GDP,
Personal Income and Outlays, international trade, and related national-account
releases. It exposes release date, time, title, and official links and was
verified as independently accessible when both BLS endpoints returned HTTP 403.

BEA does not republish missing BLS CPI or employment events. Fallback success
therefore improves official macro-calendar completeness but never claims
equivalent BLS coverage. No third-party calendar, cached fixture, inferred date,
or hardcoded event may become production fallback data.

## Retrieval and priority policy

Both adapters are isolated source attempts so the artifact can audit availability
and detect conflicting official representations.

1. Primary ICS records have priority when the same name and schedule agree.
2. An agreeing cross-agency record contributes provenance but does not create a
   duplicate event.
3. A fallback-only record remains eligible and is labelled official
   single-source Evidence.
4. Primary success remains `complete` if fallback retrieval fails because the
   authoritative source is available; the failed fallback attempt is still
   reported.
5. Primary failure plus fallback success is `partial`, with the fallback events
   retained and the primary failure classified.
6. Both unavailable produces `failed`, an empty event array, and no synthetic
   replacements.

## Event provenance contract

Every emitted event retains the existing fields:

- `source`
- `publisher`
- `source_url`
- `retrieved_at`
- `scheduled_at`
- `confidence_score` and `confidence_label`
- `content_hash`

It additionally exposes:

```json
{
  "verification_level": "official_fallback",
  "conflict_group_id": null,
  "provenance": [
    {
      "source": "bea_release_schedule",
      "publisher": "U.S. Bureau of Economic Analysis",
      "source_url": "https://www.bea.gov/news/2026/example",
      "retrieved_at": "2026-08-28T01:00:00Z",
      "scheduled_at": "2026-09-11T12:30:00Z",
      "content_hash": "sha256:...",
      "priority": 1
    }
  ]
}
```

Allowed verification levels are:

- `official_corroborated`: both official agency calendars agree;
- `official_primary`: primary ICS record only;
- `official_fallback`: fallback HTML record only;
- `official_conflict`: an official representation conflicts with another.

Confidence describes representation quality, not event impact or truth
probability. Corroborated and primary records retain `0.95`; fallback-only
records use `0.90`; conflicting records are capped at `0.60` and remain separate.

## Source-attempt contract

`economic_calendar.json` includes a `sources` array. Each attempt contains:

- source and publisher;
- source URL and priority;
- format;
- status: `available`, `unavailable`, or `invalid`;
- retrieval timestamp when a response was obtained;
- failure type, retryability, and sanitized error when unsuccessful;
- parsed and accepted event counts.

The run manifest copies this array into the calendar artifact record as
`source_health`. This makes a successful fallback distinguishable from a fully
healthy primary run without changing module execution semantics.

## Failure classification

| Failure type | Meaning | Retryable |
| --- | --- | --- |
| `primary_source_access_error` | Primary transport/access failure; fallback may be used | yes |
| `primary_source_validation_error` | Primary response is malformed or untrusted | no |
| `fallback_source_access_error` | Fallback transport/access failure | yes |
| `fallback_source_validation_error` | Fallback response is malformed or untrusted | no |
| `all_sources_unavailable` | No approved source produced valid records | derived from attempts |
| `source_conflict` | Official representations disagree on schedule | no |
| `event_validation_error` | Individual records were isolated | no |

Individual source failures live in `sources`. Artifact `failure_type` records the
condition that degraded the selected calendar result.

## Agreement and conflict handling

Events first match on a deterministic normalized release name. Because BLS and
BEA normally publish different release families, most records remain explicit
single-source official events.

- Same normalized name and same UTC `scheduled_at`: one event is emitted with
  every provenance link retained.
- Same normalized name but different UTC schedules: every source record is
  emitted as a separate event, each receives the same deterministic
  `conflict_group_id`, verification is `official_conflict`, and artifact status
  becomes `partial`.
- A record present in only one representation is not silently discarded and is
  not treated as proof that the other source is wrong.

No timestamp averaging, source-priority overwrite, fuzzy LLM match, or silent
merge is permitted. Conflict records remain factual claims about what each
official representation published.

## Validation rules

The calendar validator rejects:

- missing or duplicate source-attempt records;
- unapproved source/publisher/URL combinations (only BLS and BEA are allowed);
- malformed UTC timestamps or hashes;
- events without complete top-level provenance;
- provenance records not linked to an approved successful source attempt;
- verification levels inconsistent with provenance count/source priority;
- a conflict group containing fewer than two records or only one schedule;
- failed artifacts containing events;
- fallback success represented as primary provenance;
- predictive, causal, bullish/bearish, or trading language introduced by the
  resilience layer.

## Manifest behavior

- Primary success: calendar module may remain `success`; fallback attempt health
  is visible in `source_health`.
- Primary failed, fallback success: calendar module is `partial`; the run records
  the primary warning but downstream Evidence remains available.
- Both unavailable: calendar module is `unavailable` and the run records a
  retryable source/data failure.
- Conflict: calendar module is `partial`; both conflicting event records and
  their provenance remain publishable to downstream Evidence.
