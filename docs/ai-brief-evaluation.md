# AI Brief Evaluation Contract

> Phase 7.4-B supersedes the v1 metric layout with the calibrated
> `ai_brief_evaluation_v2` profiles defined in
> [AI Brief Evaluation Calibration](ai-brief-evaluation-calibration.md). This
> document remains the Phase 7.4-A baseline and boundary record.

## Purpose and boundary

Phase 7.4-A adds a deterministic production evaluation layer after grounded brief generation:

```text
top_intelligence.json
daily_intelligence.json
ai_market_brief.md
daily_market_brief.md
generation metadata
        |
        v
AI Brief Evaluator
        |
        v
ai_brief_evaluation.json
```

The evaluator measures whether the published writing is grounded, cited, concise, non-duplicative, and mechanically readable. It does not assess whether markets are correctly valued, whether an event truly caused a move, whether a forecast is accurate, or whether a trade should be made.

The evaluator does not call an LLM, change the generated brief, rerun generation, weaken the existing validator, rank intelligence, or affect the UI.

## Inputs

- `top_intelligence.json`: canonical Top Intelligence selection and references.
- `daily_intelligence.json`: canonical structured intelligence and provenance.
- `ai_market_brief.md`: evaluated output.
- `daily_market_brief.md`: canonical deterministic fallback.
- current-run generation metadata: copied from the grounded brief result by orchestration.

Generation metadata is validated before evaluation. No prompt, API credential, provider response, or provider error body is an evaluation input or output.

## Output contract

`ai_brief_evaluation.json` uses `ai_brief_evaluation_v1` and contains:

```json
{
  "schema_version": "1.0",
  "schema_contract": "ai_brief_evaluation_v1",
  "artifact_type": "ai_brief_evaluation",
  "run_id": "run_...",
  "generated_at": "...",
  "status": "complete",
  "generation_metadata": {},
  "validation_result": {},
  "quality_metrics": {},
  "fallback_status": {},
  "input_refs": {},
  "warnings": []
}
```

Top-level status is:

- `complete`: the applicable existing validator passed;
- `invalid`: the evaluated content failed its applicable validator or conflicts with fallback metadata;
- `unavailable`: generation metadata or output says no brief is available.

The shared freshness contract is also included. Evaluation freshness is derived from canonical Daily Intelligence timestamps; evaluation does not make stale input current.

## Metrics

### 1. Grounding compliance

For `grounded_ai`, the evaluator calls the unchanged grounded brief validator against the canonical Top and Daily artifacts.

Fields:

- `status`: `passed`, `failed`, or `not_applicable`;
- `score`: `1.0`, `0.0`, or `null`;
- `violation_count`: zero or one normalized validation failure.

For deterministic fallback, grounding compliance is `not_applicable`; the deterministic renderer validator is used instead.

### 2. Citation coverage

A citable line is any non-empty, non-heading factual line. A covered line contains a terminal `[refs: ...]` citation or is a `Source / Evidence:` reference inventory line.

Fields:

- `citable_line_count`;
- `cited_line_count`;
- `coverage_ratio`, from `0.0` to `1.0`;
- `missing_citation_count`.

Fallback Markdown is measured for observability even though its deterministic contract uses a different traceability format.

### 3. Unsupported claim detection

This metric does not independently decide truth. For grounded output it reports whether the existing grounded validator detected a contract violation.

Fields:

- `status`: `none_detected`, `detected`, or `not_applicable`;
- `detected_count`;
- normalized `reason_code`, never raw text.

Examples of normalized codes include `citation_violation`, `unsupported_reference`, `unsupported_asset`, `unsupported_event`, `unsupported_number`, `prohibited_claim`, `structure_violation`, and `validation_failure`.

### 4. Output length

- character count;
- UTF-8 byte count;
- line count;
- word/token-like unit count;
- `within_character_limit`, using the unchanged 20,000-character grounded limit.

### 5. Duplication

The evaluator normalizes substantive, non-heading lines and counts exact repeated lines. Reference-only inventory lines are excluded so repeated evidence formatting is not treated as narrative duplication.

- substantive line count;
- duplicate line count;
- unique line ratio;
- repeated line hashes, never copied raw prose.

### 6. Readability

Language-neutral mechanical indicators only:

- paragraph count;
- heading count;
- list item count;
- sentence count;
- average token-like units per sentence;
- long sentence count, using more than 35 units;
- average paragraph characters.

These metrics describe form, not investment quality or market correctness.

## Validation result

`validation_result` records:

- applicable validator: `grounded_brief_validator`, `deterministic_renderer_validator`, or `none`;
- `status`: `passed`, `failed`, or `not_applicable`;
- normalized `reason_code`;
- evaluation timestamp.

Raw validation exception messages are not published.

## Fallback status

The artifact preserves:

- whether fallback was used;
- normalized fallback reason;
- whether `ai_market_brief.md` exactly matches `daily_market_brief.md`;
- whether that relationship is consistent with generation metadata.

A grounded-AI result that is byte-identical to the fallback is permitted when explicit metadata says it was validated provider output; metadata remains the source of truth. A declared deterministic fallback that does not match the fallback file is invalid.

## Determinism and privacy

Identical inputs and evaluation timestamp produce identical metrics and run identity. File hashes preserve traceability without embedding full content in the JSON artifact.

The evaluation artifact must never contain:

- prompts;
- API keys or request headers;
- raw provider responses;
- raw exception messages;
- generated prose beyond hashes and numeric metrics.

## Production failure handling

Evaluation failure does not replace a valid brief and does not trigger another provider request. The orchestrator records the evaluation module independently. A missing evaluation artifact must not break Intelligence Web View or deterministic fallback publication.
