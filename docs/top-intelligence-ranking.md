# Phase 7.2-A Top Market Intelligence Ranking Contract

## Purpose and boundary

The Top Market Intelligence selector is a deterministic product-value layer over
`daily_intelligence.json`. It answers three questions for the current run:

1. What validated condition matters most now?
2. Why was it selected, using only facts already present in the input?
3. What observable field or scheduled timestamp should be monitored next?

The selector does not rank news articles, infer causes, predict direction, create
sentiment, or generate trading advice. It does not change any upstream signal,
regime, or risk rule. Its sole canonical input is the validated structured daily
intelligence artifact.

Canonical production flow:

```text
daily_intelligence.json
        |
        v
Top Intelligence Selector
        |
        v
top_intelligence.json
        |\
        | +--> Deterministic Brief Renderer
        +----> Intelligence Web View
```

## Candidate types

The selector may construct candidates only from these existing objects:

| Candidate type | Input section | Eligible state |
|---|---|---|
| `cross_asset_signal` | `cross_asset_signals` | `state=observed`, `condition_met=true`, data quality available |
| `market_regime` | `market_regime` | status available or partial and classification is `risk_on`, `risk_off`, or `mixed` |
| `upcoming_event` | `upcoming_events` | status scheduled, official event scheduled after selection time and within the existing 48-hour risk window |
| `market_stress` | `observed_market_stress` | status detected |
| `data_quality` | `data_quality_risks` | status detected, attention high, and it materially limits interpretation |

Raw news items, normalized news events that are not represented as an eligible
upcoming risk, `not_observed` relationships, retracted events, and legacy brief
objects are not candidates.

## Eligibility gate

Every candidate passes all applicable gates before scoring:

1. The input must pass the Phase 6.4-A validator.
2. The wrapper must have `validation_status=validated`.
3. The source artifact coverage row must have both record freshness and artifact
   freshness equal to `current`. A data-quality candidate is the sole exception:
   its freshly generated risk record may describe stale upstream records, so its
   risk artifact freshness must be `current` while its record freshness may be
   degraded.
4. The object must satisfy the type-specific state in the table above.
5. Substantive candidates must retain at least one source reference and one of:
   evidence bundle, observation, event, signal, regime dimension, or risk ID.
6. An upcoming event must retain an event ID and a source record whose quality is
   official/Tier 1. Its lifecycle cannot be expired or retracted.
7. A data-quality candidate must identify a high-attention limitation affecting a
   canonical interpretation input: market observations, macro observations,
   economic calendar, market signals, or market regime. Missing optional news or
   historical existing-evidence coverage alone is not material enough for Top 3.

The following are rejected, not down-ranked:

- stale, unknown-freshness, or unavailable source artifacts;
- `insufficient_data`, `not_observed`, unavailable, invalid, or failed objects;
- unsupported causal statements or fields;
- predictions, sentiment labels, or trading instructions;
- raw news and retracted or expired events;
- records with unresolved traceability.

## Deterministic scoring

Eligible candidates receive an integer score out of 100. The full breakdown is
published with every selected item.

| Component | Maximum | Rule |
|---|---:|---|
| Freshness | 20 | 20 only when record and artifact freshness are current; otherwise ineligible |
| Evidence quality | 20 | 20 official event; 18 source plus evidence/observation support; 14 source plus structural ID; 12 verified coverage metadata |
| Cross-asset breadth | 15 | 5 per distinct asset theme, capped at 15; broad available regime receives 15 |
| Event proximity | 15 | upcoming event: 15 within 6h, 12 within 24h, 8 within 48h; non-events receive 0 |
| Market relevance | 15 | regime 15; observed stress high/medium/low = 15/10/5; signal = 5 per related asset capped at 15; event high/medium/low = 15/10/5; material quality limitation = 10 |
| Confirmation | 10 | 10 for official event or at least two sources; 8 for at least two evidence/observation records; 6 for one resolved support chain; 4 for verified coverage metadata |
| Risk relevance | 5 | observed stress or high-impact upcoming event 5; medium event 3; market regime 3; other candidates 0 |

`total_score` is the arithmetic sum of these seven components. No hidden weight,
random value, model output, or wall-clock-dependent heuristic is allowed.

## Tie-breaking and stable identity

Candidates are ordered by:

1. total score descending;
2. type priority: market stress, upcoming event, market regime, cross-asset
   signal, material data-quality limitation;
3. scheduled timestamp ascending for upcoming events;
4. source object ID ascending.

`item_id` is a stable SHA-256-derived identifier of candidate type, source object
ID, input run ID, and selector rule-set version. Re-running with identical input
and selection time produces byte-equivalent item ordering and content.

## Semantic story grouping, diversity and duplicate suppression

Scoring is completed before grouping. Every eligible candidate receives a
deterministic `story_key` that describes its user-level narrative rather than its
artifact type. The processing order is fixed:

```text
candidate scoring
    -> story_key grouping
    -> keep highest-scoring candidate per story
    -> primary-theme diversity
    -> Top 3
```

Examples:

- an observed `risk_off` regime, equity weakness with higher VIX, and aligned
  equity/crypto weakness use `market_state:risk_off`;
- the inverse current conditions use `market_state:risk_on`;
- DXY strength observed with lower Gold, higher yields, or aligned FX quotes uses
  `macro_state:usd_strength`; the inverse uses `macro_state:usd_weakness`;
- each official scheduled event uses `event:<event_id>`;
- unrelated crypto, commodity, event, market-state, and data-quality stories keep
  separate keys.

Only the first candidate under the deterministic score/tie-break order survives
within each story group. Object category can never override this rule.

The selector prefers breadth over repetition:

- themes are `macro_rates`, `equities_volatility`, `crypto`, `commodities`,
  `upcoming_events`, `market_regime`, and `data_quality`;
- the first pass selects at most one candidate per primary theme;
- candidates sharing a primary theme and any evidence, event, signal, or risk ID
  are the same story and only the higher-ranked one survives;
- cross-asset candidates with the same primary theme and at least two-thirds
  overlap in related assets are treated as the same story;
- a second candidate from the same primary theme is never used as filler.

The selector returns at most three items. If only one or two genuinely distinct
current candidates exist, it returns one or two. If none exist, it returns no
cards and `status=unavailable`.

## Fallback and status behavior

| Selected count | Status | Behavior |
|---:|---|---|
| 3 | `complete` | Publish three ranked items |
| 1–2 | `partial` | Publish only eligible items and a `fewer_than_three_eligible_items` warning |
| 0 | `unavailable` | Publish no items and a `no_current_eligible_top_intelligence` warning |

The brief and web view must consume `top_intelligence.json`; neither presentation
path may independently rank or rebuild candidates. If the artifact is missing,
invalid, stale, or unavailable, the web view displays exactly:

> No current validated Top 3 intelligence is available.

## Output contract

`top_intelligence.json` has this shape:

```json
{
  "schema_version": "1.0",
  "artifact_type": "top_intelligence",
  "run_id": "run_..._top_...",
  "report_date": "YYYY-MM-DD",
  "generated_at": "UTC ISO-8601",
  "status": "complete | partial | unavailable",
  "rule_set_version": "top_intelligence_rules_v1",
  "input_refs": {
    "daily_intelligence_run_id": "run_..."
  },
  "candidate_count": 0,
  "eligible_count": 0,
  "selected_count": 0,
  "items": [
    {
      "rank": 1,
      "item_id": "top_...",
      "type": "cross_asset_signal | market_regime | upcoming_event | market_stress | data_quality",
      "story_key": "market_state:risk_off",
      "source_object_id": "...",
      "headline": "deterministic factual template",
      "why": "deterministic selection explanation",
      "monitor": "deterministic observable field or timestamp",
      "total_score": 0,
      "score_breakdown": {},
      "primary_theme": "...",
      "related_assets": [],
      "evidence_refs": {},
      "source_refs": [],
      "timestamps": {},
      "freshness_status": "current",
      "validation_status": "validated"
    }
  ],
  "warnings": [],
  "limitations": []
}
```

The shared freshness contract adds `source_timestamp`, `retrieved_at`,
`age_seconds`, `freshness_status`, `freshness_basis`, `stale_after_seconds`, and
`freshness_contract_version` at artifact level. Selected items always declare
`freshness_status=current`.

## Deterministic text rules

Text is assembled from allowlisted labels and validated payload fields only:

- signal: label, relationship kind, observed values, and required assets;
- regime: classification, eligible dimension count, and confidence label;
- event: official event title, scheduled timestamp, impact, and affected assets;
- stress: existing risk title, description, observed facts, and attention level;
- data quality: existing risk title, affected input, and coverage status.

`why` explains the score-driving observed evidence. `monitor` names a scheduled
time or an already-defined observable metric/coverage state. Templates must not
introduce “caused”, “will”, “expected to rise/fall”, bullish/bearish, buy/sell,
price targets, or recommendations.

## Validation rules

The validator rebuilds the expected artifact from the validated input and the same
selection timestamp, then compares deterministic content. It additionally rejects:

- more than three items, non-contiguous ranks, duplicate IDs, story keys, or
  primary themes;
- totals that do not equal the score breakdown;
- any non-current selected item;
- unresolved source, evidence, observation, event, signal, regime, or risk refs;
- missing source timestamps or freshness metadata;
- prohibited prediction, causality, sentiment, or trading fields/phrases;
- a status inconsistent with selected count.
