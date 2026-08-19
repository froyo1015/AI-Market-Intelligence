# Phase 6.2-C News Event Schema — Design Freeze

> Status: CTO-approved documentation contract. No News Adapter, external feed,
> extraction code, ranking code or LLM integration is authorized yet.

## 1. Purpose

News ingestion must preserve the difference between:

1. a publisher supplied a news item;
2. the system normalized that item into a candidate market event;
3. evidence supports an interpretation of that event;
4. market observations happened near the event.

None of these steps independently proves that the event caused a market move.

```text
News source
    ↓
news_items.json            source-grounded records
    ↓
validation + normalization
    ↓
events.json                canonical candidate events
    ↓
deduplication + mapping
    ↓
evidence.json              supported or unconfirmed relationships
```

## 2. Scope and Non-goals

Phase 6.2-C MVP scope:

- one explicitly approved free or public news source;
- a bounded 24-hour lookback with a six-hour overlap between daily runs;
- at most 100 retained items per source and run;
- headline and source-provided metadata only;
- deterministic validation, exact deduplication, event typing and mapping;
- no LLM extraction, sentiment model or market-impact prediction.

Not in scope:

- scraping full copyrighted articles;
- storing article bodies;
- social-media rumours or anonymous claims;
- embeddings or semantic vector search;
- automatic causal explanations;
- buy/sell recommendations;
- changing the existing market, macro, calendar, Pages or Telegram modules.

## 3. Artifact Boundary: `news_items.json`

`news_items.json` is the immutable adapter output. Provider payloads must not
enter `events.json`, Evidence or Intelligence directly.

### 3.1 Envelope

| Field | Type | Required | Meaning |
|---|---|---:|---|
| `schema_version` | string | yes | Starts at `1.0` |
| `artifact_type` | string | yes | Fixed as `news_items` |
| `run_id` | string | yes | Shared daily run identifier |
| `report_date` | string | yes | Report date in the configured report timezone |
| `generated_at` | string | yes | UTC retrieval completion time |
| `window_start` / `window_end` | string | yes | Inclusive UTC ingestion window |
| `source` | string | yes | Adapter identifier |
| `status` | enum | yes | `complete`, `partial` or `failed` |
| `failure_type` | string/null | yes | Machine-readable failure classification |
| `retryable` | boolean | yes | Whether a later retry may reasonably succeed |
| `warnings` | array[string] | yes | Coverage and rejection warnings |
| `accepted_count` / `rejected_count` | integer | yes | Auditable source-record counts |
| `rejections` | array[RejectionRecord] | yes | Sanitized rejected-record audit entries |
| `items` | array[NewsItem] | yes | Valid accepted source records only |

Failure types:

| Failure type | Retryable | Meaning |
|---|---:|---|
| `source_access_error` | yes | Timeout, rate limit, authentication or transport failure |
| `source_validation_error` | no | Response violates the approved source contract |
| `item_validation_error` | no | One or more records are malformed; artifact may remain partial |
| `licensing_policy_error` | no | Payload contains content the project is not permitted to retain |

A valid source response containing zero items is `complete` with
`failure_type: null`. It is not a source failure.

### 3.2 `NewsItem`

| Field | Type | Required | Meaning |
|---|---|---:|---|
| `item_id` | string | yes | Deterministic internal source-item ID |
| `provider_item_id` | string/null | yes | Original feed ID when supplied |
| `headline` | string | yes | Exact source headline after whitespace normalization |
| `source_excerpt` | string/null | yes | Source-provided excerpt, capped at 500 characters |
| `publisher` | string | yes | Original publisher, not merely the feed distributor |
| `provider` | string | yes | Adapter/feed provider |
| `source_type` | enum | yes | `official`, `original_publisher`, or `aggregator` |
| `quality_tier` | integer | yes | `1`, `2` or `3` according to the policy below |
| `source_url` | string | yes | URL supplied by the provider |
| `canonical_url` | string | yes | Normalized original or canonical publisher URL |
| `published_at` | string | yes | Publisher timestamp in UTC |
| `retrieved_at` | string | yes | Adapter retrieval timestamp in UTC |
| `language` | string | yes | BCP 47 language tag; no implicit translation |
| `content_hash` | string | yes | SHA-256 of the retained normalized fields |

The item contract stores no inferred assets, topics, sentiment or impact.
Those belong to normalization and mapping, not source ingestion.

### 3.3 `RejectionRecord`

Rejected source records do not enter `items`. The audit entry retains only:

| Field | Type | Required | Meaning |
|---|---|---:|---|
| `provider_item_id` | string/null | yes | Provider ID when safely available |
| `source_url` | string/null | yes | Source URL when valid enough to retain |
| `reason_codes` | array[string] | yes | Versioned deterministic rejection codes |
| `matched_item_id` | string/null | yes | Accepted canonical item when rejected as duplicate |
| `matched_event_id` | string/null | yes | Existing canonical event when already resolved |

No headline, excerpt or article content is retained for a licensing-policy
rejection.

### 3.4 Copyright and retention rules

- Never store full article text, paywalled content or copied page HTML.
- Retain only headline, canonical URL, timestamps, publisher metadata and an
  optional source-provided excerpt capped at 500 Unicode characters.
- `content_hash` covers only retained fields; it does not imply possession of
  the article body.
- Remove known tracking parameters from canonical URLs without changing
  content-identifying query parameters.
- Rejection audit entries may retain identifiers and reason codes, but not
  prohibited content.

## 4. Source Quality Policy

| Tier | Accepted source class | Use in evidence |
|---:|---|---|
| 1 | Government agency, regulator, exchange, central bank, company IR or protocol foundation | May support a factual event directly |
| 2 | Identified original publisher with an approved public feed and clear provenance | Supports a reported event; corroboration preferred |
| 3 | Aggregator that retains a resolvable original publisher URL | Discovery only; cannot independently support a published conclusion |

Unknown publishers, URL shorteners without a resolvable destination, anonymous
social posts and feeds without publication timestamps are rejected.

Source selection is an implementation gate. The schema does not approve a
provider or its redistribution terms.

## 5. Normalized News Event in `events.json`

The existing canonical Event contract remains authoritative. News normalization
adds a versioned `normalization` object rather than copying provider-specific
fields into the event root.

### 5.1 Required news-event fields

| Existing field | News rule |
|---|---|
| `event_id` | Deterministic from canonical event key, never from run order |
| `event_type` | Controlled category; unknown types are rejected |
| `status` | Data status, not a truth or market-impact judgment |
| `title` | Factual normalized title; must not add facts absent from sources |
| `summary` | `null` unless a deterministic source-grounded summary is available |
| `occurred_at` | Event time only when explicitly stated; otherwise `null` |
| `scheduled_at` | Used only for a future scheduled event confirmed by a valid source |
| `country_codes` | Explicit source entity or versioned rule mapping |
| `entity_ids` | Canonical entities resolved by exact alias rules |
| `candidate_assets` | Possible relevance, never asserted price impact |
| `topics` | Controlled vocabulary and versioned mapping rules |
| `source_refs` | All retained valid sources supporting the canonical event |
| `canonical_hash` | Stable event deduplication key |
| `duplicate_of` | Canonical event ID after a deterministic merge |

### 5.2 `normalization` object

```json
{
  "input_item_ids": ["nws_example_001"],
  "method": "headline_rules",
  "rule_version": "news_normalization_v1",
  "normalized_action": "publishes_announcement",
  "event_key_fields": ["event_type", "entity_ids", "normalized_action"],
  "mapping_rule_ids": ["entity_alias_v1", "topic_asset_map_v1"],
  "extraction_quality_score": 0.82,
  "mapping_quality_score": 0.75,
  "verification_level": "single_source"
}
```

Allowed `method` values for the MVP are `publisher_structured` and
`headline_rules`. `llm` is prohibited.

Quality scores measure deterministic rule coverage and mapping specificity.
They are not probabilities that a report is true. Source quality and event
verification remain separate dimensions.

Allowed `verification_level` values:

- `official`: supported by a Tier 1 original source;
- `corroborated`: two or more independent valid publishers report the event;
- `single_source`: one Tier 2 source reports the event;
- `unverified`: only Tier 3 or conflicting sources; ineligible for conclusions.

### 5.3 Event lifecycle

The existing root `status` continues to describe data health. It must not be
overloaded with the event's evolving verification state. News events add these
fields:

| Field | Type | Required | Meaning |
|---|---|---:|---|
| `event_version` | integer | yes | Monotonic version for the stable `event_id` |
| `lifecycle_status` | enum | yes | Current event lifecycle state |
| `lifecycle_updated_at` | string | yes | UTC time of the latest state transition |
| `lifecycle_reason_code` | string | yes | Deterministic rule or source action causing the transition |
| `retraction_source_ids` | array[string] | yes | Required for `retracted`; otherwise empty |

Allowed lifecycle states:

- `new`: a valid candidate event was created from one or more NewsItems;
- `validated`: schema, provenance and deterministic mappings passed;
- `confirmed`: occurrence is supported by a Tier 1 source or the approved
  independent-corroboration rule;
- `expired`: outside the active intelligence window but retained for audit;
- `retracted`: an authoritative source retracted or materially corrected the
  event; it is ineligible for publication as current fact.

The same canonical event keeps the same `event_id` as it moves through its
lifecycle. A transition increments `event_version`; it must not create a new
event merely because verification improved. `confirmed` applies only to event
occurrence and never confirms claimed market impact or causality.

Allowed transitions for the first implementation are:

| From | To |
|---|---|
| `new` | `validated`, `retracted`, `expired` |
| `validated` | `confirmed`, `retracted`, `expired` |
| `confirmed` | `retracted`, `expired` |
| `expired` | `retracted` |
| `retracted` | terminal state |

The initial persisted version may start at the highest state supported within
one deterministic run. Only a change from a previously persisted state
increments `event_version`.

## 6. Controlled Event Types and Topics

Initial event types:

- `macro_release`
- `central_bank`
- `company`
- `crypto`
- `geopolitical`
- `commodity`
- `regulatory`

Initial topics:

- `monetary_policy`
- `inflation`
- `labor_market`
- `earnings`
- `corporate_guidance`
- `regulation`
- `crypto_market_structure`
- `energy_supply`
- `geopolitical_risk`

Adding a type or topic requires a schema-minor update, mapping rules and tests.
Free-form topics are not accepted.

## 7. Deterministic Deduplication Contract

### Exact duplicate

Merge when any of the following matches:

- canonical URL;
- provider plus provider item ID;
- retained content hash;
- normalized headline plus publisher and a two-hour publication bucket.

### Candidate event duplicate

Items may be candidates for the same event when all are true:

- event type and normalized action match;
- at least one canonical entity matches;
- publication timestamps are within 12 hours;
- deterministic normalized-title token similarity meets the frozen threshold.

The deduplicator must record the rule ID and score. Embeddings and LLM semantic
matching remain deferred. Ambiguous candidates remain separate and receive a
warning rather than being force-merged.

## 8. Evidence and Causality Rules

- A news item proves only that a named publisher reported the retained text.
- A Tier 1 source may establish an official action or release, but not its
  market impact.
- Temporal proximity between an event and a price move supports only
  `associated`; it never supports `caused`.
- `single_source` events may be listed with the source but require additional
  evidence before becoming an intelligence conclusion.
- Tier 3 or `unverified` events cannot independently create an Evidence bundle
  eligible for the public Brief.
- Conflicting sources must remain visible as limitations.
- Every mapped asset must identify its mapping rule and mapping-quality score.
- A `retracted` event cannot support new evidence and must invalidate any
  unresolved public-intelligence candidate derived from it.

## 9. Validation and Rejection Rules

Reject a NewsItem when:

- headline, publisher, canonical URL or publication time is missing;
- the canonical URL is not HTTP(S) or cannot identify an allowed publisher;
- publication time is in the future beyond the clock-skew allowance;
- the item falls outside the bounded ingestion window;
- the language is unsupported and no source-supplied translation exists;
- it contains only promotional, sponsored or anonymous content;
- retention would violate the approved source policy.

Reject or quarantine a normalized event when:

- an input item ID or source reference cannot be resolved;
- the normalized title introduces unsupported facts or numbers;
- entity, topic or asset mappings have no versioned rule;
- a concrete time, number or quote cannot be traced to retained source fields;
- `verification_level` conflicts with source quality and source count;
- lifecycle transitions are invalid, go backwards without a reason code, or
  mark an event retracted without an authoritative source reference;
- causal language appears in the event title or summary.

## 10. Example Adapter Artifact

```json
{
  "schema_version": "1.0",
  "artifact_type": "news_items",
  "run_id": "run_20260819_daily",
  "report_date": "2026-08-19",
  "generated_at": "2026-08-19T22:00:00Z",
  "window_start": "2026-08-18T16:00:00Z",
  "window_end": "2026-08-19T22:00:00Z",
  "source": "approved_source_adapter",
  "status": "complete",
  "failure_type": null,
  "retryable": false,
  "warnings": [],
  "accepted_count": 1,
  "rejected_count": 0,
  "rejections": [],
  "items": [
    {
      "item_id": "nws_20260819_example_a1b2c3d4",
      "provider_item_id": "provider-123",
      "headline": "Publisher-supplied factual headline",
      "source_excerpt": null,
      "publisher": "Identified publisher",
      "provider": "approved_source",
      "source_type": "original_publisher",
      "quality_tier": 2,
      "source_url": "https://publisher.example/item/123",
      "canonical_url": "https://publisher.example/item/123",
      "published_at": "2026-08-19T20:00:00Z",
      "retrieved_at": "2026-08-19T22:00:00Z",
      "language": "en",
      "content_hash": "sha256:example"
    }
  ]
}
```

The example contains placeholders and must never be shipped as live data.

## 11. Implementation Gate and Acceptance Criteria

Coding Phase 6.2-C may begin only after approval of:

1. one initial source and its usage/retention terms;
2. supported language set;
3. exact source-quality tier;
4. ingestion window and item cap;
5. entity aliases and controlled topic mappings;
6. deterministic near-duplicate similarity threshold;
7. lifecycle transition rules and retraction authority policy.

Implementation acceptance criteria:

- source failure produces an explicit classified artifact with no fake items;
- 100% of accepted items have publisher, canonical URL and both timestamps;
- no full article body is stored;
- IDs and hashes are stable for identical retained input;
- exact duplicates collapse deterministically;
- ambiguous near duplicates are not force-merged;
- every normalized event resolves to NewsItem and SourceReference IDs;
- event lifecycle updates preserve stable IDs and increment `event_version`;
- retracted events cannot support current intelligence;
- no causal claim, sentiment score or predicted impact is generated;
- existing Market, Macro, Calendar and Evidence Foundation tests remain green.
