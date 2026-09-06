# AI Brief Evaluation Calibration

## Purpose

Phase 7.4-B calibrates evaluation to the contract that produced the published
brief. A grounded AI narrative and a deterministic renderer output have
different structures and must not be scored as if they were interchangeable.
The selected profile is derived only from validated generation metadata.

This layer evaluates contract quality. It does not evaluate market correctness,
forecast accuracy, investment merit, or trading performance.

## Profile selection

| Generation metadata | `evaluation_mode` | Profile |
| --- | --- | --- |
| `generation_mode: grounded_ai` | `grounded_ai` | `grounded_ai_profile` |
| `generation_mode: deterministic_fallback` | `deterministic_fallback` | `deterministic_fallback_profile` |

An unavailable generation does not select a profile or produce a successful
evaluation artifact. In production, a missing grounded-brief artifact blocks
the evaluation module and is recorded by orchestration.

Profile selection is deterministic. Content similarity or byte comparison must
not select the evaluation profile. Byte equality remains only a fallback
integrity check after the metadata-selected fallback profile is active.

## `grounded_ai_profile`

This profile evaluates natural-language output written from validated
intelligence artifacts:

- `grounding_compliance`: result from the unchanged grounded brief validator;
- `citation_coverage`: factual lines carrying terminal `[refs: ...]` or an
  explicit `Source / Evidence:` inventory;
- `unsupported_claim_detection`: normalized result from the existing validator;
- `reference_integrity`: whether cited identifiers are present in the canonical
  Top Intelligence or Daily Intelligence reference universe;
- `duplication`: exact normalized repeated substantive lines;
- `readability`: language-neutral structural and sentence-length indicators.

No metric in this profile estimates whether a statement is economically true.
The profile does not rerun the LLM or introduce a second claims validator.

## `deterministic_fallback_profile`

This profile evaluates the deterministic presentation contract:

- `schema_validity`: result from the unchanged deterministic renderer validator;
- `artifact_completeness`: presence of the fallback Markdown and both canonical
  structured input artifacts;
- `freshness_metadata`: shared freshness contract availability and validity on
  Daily Intelligence and Top Intelligence;
- `reference_preservation`: canonical reference identifiers remain present in
  the renderer output;
- `section_completeness`: required deterministic report headings are present.

Citation coverage, unsupported-claim detection, duplication, and readability
are not emitted for fallback output. The fallback uses structured traceability
blocks rather than sentence-level `[refs: ...]`, so applying the grounded
citation metric would create a false quality failure.

## Calibrated artifact contract

`ai_brief_evaluation_v2` adds:

```json
{
  "evaluation_mode": "grounded_ai",
  "evaluation_profile": "grounded_ai_profile",
  "quality_metrics": {
    "grounding_compliance": {},
    "citation_coverage": {},
    "unsupported_claim_detection": {},
    "reference_integrity": {},
    "duplication": {},
    "readability": {}
  }
}
```

For deterministic fallback, `quality_metrics` contains exactly the five
fallback metrics listed above. Inapplicable metric groups are omitted rather
than populated with misleading zero scores.

## Reference integrity

The evaluator builds an allowed reference universe from validated structured
inputs. It includes run IDs, object IDs, source IDs, event IDs, observation IDs,
evidence IDs, signal IDs, risk IDs, regime dimension IDs, evidence bundle IDs,
and coverage identifiers. Grounded references are parsed from `[refs: ...]` and
`Source / Evidence:` lines. The output reports counts and hashes only; it does
not copy generated prose or raw provider output into the evaluation artifact.

For fallback output, required identifiers are collected from the same canonical
inputs. Preservation is complete only when every required identifier occurs in
the exact deterministic rendering. The unchanged renderer validator remains the
authoritative schema check.

## Freshness and completeness

Fallback freshness checks the shared freshness contract on Daily Intelligence
and Top Intelligence separately. It records checked, valid, current, stale,
unavailable, and unknown counts. Stale data is reported as stale; it is not
silently treated as missing or current.

Fallback artifact completeness is a structural availability check only. It does
not claim that all market sources are complete. Source degradation remains the
responsibility of upstream coverage and freshness contracts.

## Required deterministic sections

The fallback profile checks these renderer headings:

- `# Daily Market Intelligence Brief`
- `# Today's Top Market Intelligence`
- `## Data Quality and Coverage`
- `## Current Market Regime`
- `## Cross-Asset Observations`
- `## Upcoming Event Risks`
- `## Data Quality Risks`
- `## Observed Market Stress`
- `## Sources and Provenance`

The exact deterministic renderer validation is stricter than this heading
inventory. Section completeness exists as an observable production metric.

## Failure rules

- A grounded validator failure produces `status: invalid` under the grounded
  profile with a normalized reason code.
- A declared fallback that differs from `daily_market_brief.md` is invalid.
- An invalid deterministic rendering is invalid under `schema_validity`.
- A valid deterministic fallback must not fail because it lacks grounded-AI
  sentence citations or exceeds a grounded-AI prose limit.
- Evaluation never changes or replaces either brief artifact.

## Security and boundaries

The calibrated artifact may contain metadata, counts, booleans, timestamps, and
content/reference hashes. It must not contain prompts, API credentials, request
headers, raw provider responses, raw exceptions, or copied generated prose.
No LLM provider, validator rule, intelligence object, ranking result, or UI is
modified by this phase.
