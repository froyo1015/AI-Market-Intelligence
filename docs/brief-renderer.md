# Phase 6.4-B1 Deterministic Brief Renderer Contract

> Status: implementation contract. The renderer is a presentation-only
> boundary. It does not call an LLM, generate analysis, predict markets,
> produce sentiment or give trading recommendations.

## 1. Boundary

```text
daily_intelligence.json
        ↓
Standalone contract validation
        ↓
Deterministic Markdown renderer
        ↓
daily_market_brief.md
```

The renderer accepts exactly one `daily_intelligence_v1` artifact. It validates
the artifact's envelope, section types, object counts, timestamps, validation
statuses and internal provenance resolution before rendering. The renderer has
no access to market adapters, raw source payloads or an LLM.

The upstream composer remains the authority that validates Signal, Regime and
Risk payloads against their source artifacts. Because B1 intentionally accepts
one file only, its standalone validator verifies the composed artifact's
internal integrity; it does not claim to re-run the four upstream validators.

## 2. Render result schema

The in-memory renderer result contains:

| Field | Type | Meaning |
|---|---|---|
| `schema_contract` | string | Fixed `deterministic_brief_renderer_v1` |
| `source_run_id` | string | Exact `daily_intelligence.run_id` |
| `report_date` | string | Exact input report date |
| `source_generated_at` | timestamp | Exact input generation time |
| `source_status` | enum | `available`, `partial` or `unavailable` |
| `markdown` | string | Complete deterministic report |

The only persisted B1 artifact is UTF-8 Markdown at
`src/output/daily_market_brief.md`. No render-time clock is included, so the
same valid input always produces byte-identical output.

## 3. Fixed report sections

Sections appear exactly in this order:

1. report envelope;
2. Data Quality and Coverage;
3. Current Market Regime;
4. Cross-Asset Observations;
5. Upcoming Event Risks;
6. Data Quality Risks;
7. Observed Market Stress;
8. Sources and Provenance;
9. Scope Limitations.

All Signal and Risk objects retain their upstream order. Empty sections display
`- None in validated input.` The renderer does not move, filter, select or rank
objects.

## 4. Object rendering rules

Each rendered intelligence object includes:

- exact object ID and object type;
- source artifact, source run and source generation timestamp;
- `validation_status` and original `data_status`;
- observed, scheduled and detected timestamps;
- fixed payload fields appropriate to its existing object type;
- every provenance-reference array, including empty arrays.

Object metadata and references are placed in a standard Markdown/HTML
`details` block so the main report remains scannable while the full audit trail
stays in the same artifact.

Signal values are copied from `observed_values` as asset, metric, value, unit,
time, observation ID and source ID. Regime output copies classification,
confidence and dimensions. Risk output copies title, description, category,
status, attention level, time window, observed facts and verification.

Missing values are displayed as `unknown`. The renderer never substitutes a
neutral Regime, guessed event, inferred explanation or placeholder fact.

## 5. Evidence and provenance preservation

Every object prints the common reference keys in fixed order:

- `artifact_run_ids`
- `evidence_bundle_ids`
- `source_ids`
- `observation_ids`
- `event_ids`
- `evidence_ids`
- `signal_ids`
- `regime_dimension_ids`
- `risk_ids`
- `coverage_inputs`

Evidence-layer IDs must resolve in `provenance_catalog`. Signal IDs must resolve
to rendered Signal objects, Regime Dimension IDs to the preserved Regime
payload, Risk IDs to rendered Risk objects, and artifact runs to `input_refs`,
coverage or a source wrapper. The Sources and Provenance section copies source
identity, publisher, title, URL, publication time and retrieval time.

## 6. Data-quality behavior

The report preserves without rewriting:

- top-level status;
- every deterministic warning code;
- every coverage row and its validation, data and freshness statuses;
- artifact age and maximum age;
- every Data Quality Risk object;
- every input limitation.

`partial` and `unavailable` inputs still render a report so the absence or age
of intelligence remains visible. These states never become `available` during
rendering.

## 7. Markdown safety and formatting

- Dynamic values are single-line escaped before entering Markdown.
- Tables escape pipe characters.
- Lists and reference arrays use stable input order.
- Dictionaries use sorted keys.
- Numeric values are copied without analytical transformations.
- The output ends with one newline and is written atomically.

## 8. Validation and failure rules

Rendering fails before writing when:

- the input is not `daily_intelligence_v1`;
- required sections or fields are missing or have the wrong type;
- an object is not marked `validated`;
- object counts or section types do not match;
- IDs are duplicated or provenance references do not resolve;
- timestamps are malformed or reference arrays are not sorted and unique;
- an unknown object type is present.

Rendered-output validation regenerates the Markdown from the same input and
requires an exact byte match. This detects removed warnings, references,
objects, timestamps or reordered content.

## 9. Explicit exclusions

Phase 6.4-B1 does not implement:

- LLM or AI text generation;
- summaries, opinions or causal explanations;
- forecasts or predictions;
- sentiment or bullish/bearish labels;
- ranking or “top” selections;
- trading signals or recommendations;
- UI, Pages, Telegram, scheduler or workflow changes.
