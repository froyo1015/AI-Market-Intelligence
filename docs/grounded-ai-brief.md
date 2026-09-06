# Phase 7.2-B Grounded AI Market Brief Contract

## Purpose and boundary

The Grounded AI Market Brief adds a constrained writing layer after validated
selection and intelligence assembly. The LLM is a writer, not an analyst. It may
improve readability, but it may not add, remove, rank, reinterpret, or infer
market facts.

```text
top_intelligence.json
        +
daily_intelligence.json
        |
        v
Grounded Prompt Builder
        |
        v
Provider-neutral LLM Adapter
        |
        v
Grounded Output Validator
        |
        v
ai_market_brief.md
```

The existing `src/ai/` Phase 2 snapshot analyst is a deprecated, independent
manual path and is not reused. The canonical writer lives in
`src/grounded_brief/`. No LLM provider, API key, model, or paid service is
silently selected. A caller may inject an adapter implementing the frozen
`generate(prompt) -> Markdown` protocol. Without a configured adapter,
production uses the deterministic fallback.

## Canonical inputs

Only these artifacts may supply factual content:

- `src/output/top_intelligence.json`
- `src/output/daily_intelligence.json`

The deterministic fallback is read only from:

- `src/output/daily_market_brief.md`

The prompt builder accepts the following fields.

### Top Intelligence

- artifact metadata: `run_id`, `report_date`, `generated_at`, `status`,
  `freshness_status`, `warnings`, `limitations`;
- item identity and order: `rank`, `item_id`, `type`, `story_key`,
  `source_object_id`;
- approved wording inputs: `headline`, `why`, `monitor`;
- score and scope: `total_score`, `primary_theme`, `related_assets`;
- traceability: `evidence_refs`, `source_refs`, `timestamps`,
  `freshness_status`, `validation_status`.

The LLM must reproduce the existing Top order and exact headlines. It cannot
re-score, replace, merge, split, or supplement selected items.

### Daily Intelligence

- artifact metadata, status, warnings, limitations, coverage, and data windows;
- validated market-regime wrapper and payload;
- validated cross-asset signal wrappers and payloads;
- upcoming-event, market-stress, and data-quality risk wrappers and payloads;
- `provenance_catalog` records;
- all wrapper timestamps and evidence references.

Raw source payloads, raw news text, legacy reports, external knowledge, and web
content are never included.

## Prompt contract

The prompt has four immutable parts:

1. role boundary: neutral writer over supplied facts only;
2. exact Markdown output structure;
3. prohibited language and grounding rules;
4. canonical JSON enclosed by non-executable input markers.

Required Markdown structure:

```markdown
# Daily Market Intelligence Brief

## Today's Top 3

### 1. <exact selected headline>
<short explanation> [refs: <resolved IDs>]
Why it matters: ... [refs: <resolved IDs>]
Watch next: ... [refs: <resolved IDs>]
Source / Evidence: <resolved IDs>

## Market Regime
...

## Cross-Asset Signals
...

## Risks & Next 48 Hours
...

## Data Quality
...
```

If fewer than three items were selected, only those items appear. The heading
remains `Today's Top 3` as the product slot name; the LLM must not add filler.

Every non-heading factual line must end in one citation block:

```text
[refs: id_1, id_2]
```

`Source / Evidence:` is the only inventory line and contains the same resolved
IDs without prose. Empty sections use a neutral availability statement citing
the relevant artifact run ID.

## Citation rules

Allowed citation IDs are constructed mechanically from the two inputs:

- Top item IDs and source object IDs;
- input and source artifact run IDs;
- evidence bundle IDs;
- source IDs;
- observation IDs;
- event IDs;
- evidence IDs;
- signal IDs;
- regime dimension IDs;
- risk IDs;
- coverage input identifiers.

Every cited ID must resolve. Every Top item block must cite its `item_id` and at
least one of its evidence, event, signal, risk, regime, source, observation, or
artifact references. Each remaining section must cite at least one ID from the
corresponding validated input object, or the daily-intelligence run ID for an
explicit unavailable statement. Citations may be shortened in count, but the
traceability chain cannot be removed.

## Prohibited claims

The output must not contain:

- new assets, prices, values, timestamps, events, sources, or identifiers;
- an event or relationship not present in the input;
- causal language such as “caused”, “because of”, “led to”, “driven by”,
  “導致”, “造成”, or “推動”;
- predictive language such as “will”, “expected”, “likely”, “forecast”,
  “預計”, “將會”, or future price direction;
- bullish/bearish or equivalent directional calls;
- buy, sell, hold, allocation, position, target, or recommendation language;
- claims of real-time data when timestamps describe delayed/daily data;
- a different Top order, headline, or item count.

Neutral co-observation is allowed: “Gold strengthened while the dollar
weakened.” Unsupported causality is not: “The dollar decline caused Gold to
rise.” Neutral monitoring language is allowed: “Watch whether dollar strength
persists.” A predicted outcome is not: “Gold will fall.”

## Output validation

Validation occurs before any generated text can replace the output file:

1. required headings exist exactly once and in contract order;
2. Top item count, rank, order, and headline exactly match
   `top_intelligence.json`;
3. every non-heading factual line has a `[refs: ...]` block;
4. every citation resolves to the canonical reference registry;
5. each Top block cites its item ID and an additional support reference;
6. each report section preserves at least one corresponding reference;
7. uppercase asset-like symbols must belong to the input asset registry;
8. event vocabulary and event IDs must resolve to an input event;
9. every numerical token outside references/headings must occur verbatim in the
   canonical JSON, except the fixed report labels `3` and `48`;
10. unsupported causal, predictive, sentiment, or trading language is rejected;
11. output size is bounded and Markdown/HTML injection is rejected.

Validation failure is treated exactly like provider failure. Invalid text is
never partially published.

## Fallback and failure behavior

The pipeline always writes `ai_market_brief.md` atomically.

| Condition | Result | Pipeline status |
|---|---|---|
| Adapter returns valid grounded Markdown | Write validated LLM text | `generated` |
| No adapter configured | Copy deterministic brief | `fallback` |
| Adapter timeout/error/empty response | Copy deterministic brief | `fallback` |
| Grounded validator rejects response | Copy deterministic brief | `fallback` |
| Canonical JSON invalid or deterministic fallback missing | Do not fabricate output; raise hard input error | `failed` |

The returned run result records provider name, mode, failure category, and safe
message. It never records API keys or prompt secrets. The LLM module is a soft
enhancement: orchestration and Pages publication remain usable when it is
unavailable.

Fallback bytes are copied unchanged from `daily_market_brief.md`. Repeated
fallback runs over the same file are therefore byte-identical.
