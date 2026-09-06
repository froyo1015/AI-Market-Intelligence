# Generation Metadata Contract

## Purpose

Phase 7.2-D makes AI brief generation state an explicit backend contract. The canonical record is `generation_metadata` on the `grounded_ai_brief` module in `run_manifest.json`.

The browser must treat this record as the primary source of truth. Comparing `ai_market_brief.md` with `daily_market_brief.md` remains a legacy compatibility fallback only when generation metadata is absent or invalid.

## Contract

```json
{
  "generation_mode": "grounded_ai",
  "generation_status": "success",
  "generated_at": "2026-09-01T00:00:00Z",
  "freshness_status": "current",
  "validation_status": "validated",
  "provider": "provider_identifier",
  "fallback_reason": null
}
```

Required fields and allowed values:

| Field | Values / rule |
|---|---|
| `generation_mode` | `grounded_ai`, `deterministic_fallback`, `unavailable` |
| `generation_status` | `success`, `fallback`, `failed` |
| `generated_at` | UTC ISO-8601 timestamp |
| `freshness_status` | `current`, `stale`, `unavailable`, `unknown` |
| `validation_status` | `validated`, `unavailable`, `unknown` |
| `provider` | stable provider identifier, or `null` when no provider is configured |
| `fallback_reason` | normalized reason for fallback/failure; otherwise `null` |

Valid state combinations:

- `grounded_ai` + `success` + `validated` requires a non-empty provider and a null fallback reason.
- `deterministic_fallback` + `fallback` + `validated` requires a normalized fallback reason.
- `unavailable` + `failed` requires a normalized failure reason and cannot claim validated output.

## Normalized fallback reasons

- `no_provider_configured`
- `provider_timeout`
- `provider_rate_limit`
- `invalid_llm_output`
- `malformed_provider_response`
- `provider_error`
- `pipeline_failure`
- `missing_generation_metadata`

Provider messages and raw responses are not copied into this metadata.

## Freshness and validation

For a successful grounded brief or deterministic fallback, freshness is inherited from `daily_intelligence.json`. Generation does not make stale intelligence current.

Both outputs are marked `validated`: grounded output has passed the grounded brief validator; fallback output is the existing validated deterministic renderer artifact. If the pipeline cannot produce an output, freshness and validation are `unavailable`.

## Manifest integration

The orchestrator captures the structured return value from the grounded brief runner and writes it into the corresponding module record. The run manifest validator requires and validates this metadata for `grounded_ai_brief`.

No additional public artifact is needed. The generation record remains linked to the AI brief artifact hash, module timestamps, dependencies, freshness, and publication approval already present in the manifest.

## Publication boundary

The metadata must never contain:

- API keys or credentials;
- internal prompts;
- raw provider responses;
- provider request headers;
- secret environment names;
- unnormalized exception messages.

Only the provider identifier and normalized outcome are public.

## Legacy compatibility

If an older manifest lacks valid `generation_metadata`, the web view may compare the two published brief files:

- exact match: `deterministic_fallback`;
- otherwise: `grounded_ai`;
- missing AI brief: `unavailable`.

The UI exposes this as compatibility behavior only. New production manifests must always contain explicit generation metadata.
