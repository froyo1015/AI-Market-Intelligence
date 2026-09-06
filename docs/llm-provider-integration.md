# Real Grounded LLM Provider Integration

## Provider choice and boundary

Phase 7.3 integrates the OpenAI Responses API behind the existing `GroundedLLMAdapter` protocol:

```python
class GroundedLLMAdapter(Protocol):
    provider_name: str
    def generate(self, prompt: str) -> str: ...
```

The adapter receives the existing grounded prompt and returns Markdown. It does not build prompts, validate claims, publish files, rank intelligence, or select fallback content. The existing pipeline remains responsible for validation and atomic deterministic fallback.

Provider identifier: `openai_responses`.

The adapter sends one stateless text request to `POST /v1/responses`. It supplies no tools, no previous response, no conversation, no web search, and no autonomous continuation. Responses are not requested for provider-side storage (`store: false`). See the official [Responses API create reference](https://developers.openai.com/api/reference/cli/resources/responses/methods/create).

## Environment variables

| Variable | Required | Default | Constraint |
|---|---:|---|---|
| `OPENAI_API_KEY` | For grounded AI | none | Missing/blank selects deterministic fallback without failing the workflow |
| `OPENAI_GROUNDED_BRIEF_MODEL` | No | `gpt-5.6-luna` | Non-empty model identifier |
| `OPENAI_GROUNDED_BRIEF_TIMEOUT_SECONDS` | No | `30` | 5–120 seconds |
| `OPENAI_GROUNDED_BRIEF_MAX_OUTPUT_TOKENS` | No | `2400` | 256–4096 tokens |
| `OPENAI_GROUNDED_BRIEF_MAX_INPUT_CHARS` | No | `200000` | 10,000–500,000 characters |
| `OPENAI_GROUNDED_BRIEF_TRANSIENT_RETRIES` | No | `1` | 0 or 1 only |

Only `OPENAI_API_KEY` is secret. GitHub Actions reads it from `secrets.OPENAI_API_KEY`. Model and limit settings may use repository variables or the safe defaults.

## Model configuration

The default model is `gpt-5.6-luna`, selected for a daily, constrained writing workload where cost and latency matter. The model is configurable without code changes. No model name is embedded in the prompt builder or validator.

The request uses:

- `max_output_tokens` from the bounded configuration;
- `tools: []`;
- `tool_choice: "none"`;
- `parallel_tool_calls: false`;
- `store: false`;
- `background: false`;
- `truncation: "disabled"`;
- plain text output only.

## Timeout and retry policy

The default request timeout is 30 seconds.

A normal successful daily run makes exactly one provider request. At most one retry is permitted, and only for:

- network/transport interruption;
- timeout;
- HTTP 408 or 409;
- HTTP 429 rate limit;
- HTTP 5xx provider failure.

Non-transient HTTP errors and malformed responses are not retried. Grounded validator rejection occurs after the adapter returns and is never retried. There is no repair prompt or follow-up generation.

## Token and cost controls

- one request in the normal path;
- maximum two HTTP requests only after a transient failure;
- input contains only the existing validated Top Intelligence and Daily Intelligence prompt contract;
- 200,000-character default input ceiling;
- 2,400-token default output ceiling;
- existing 20,000-character validator ceiling remains unchanged;
- no tools, browsing, files, images, agents, or multi-turn conversation;
- no background generation or polling;
- no automatic SDK retry layer.

If input exceeds its ceiling, the provider is not called and deterministic fallback is used.

## Response handling

Only completed assistant `output_text` items are accepted. The adapter rejects:

- invalid JSON;
- missing/empty output text;
- incomplete or failed response state;
- tool-call output;
- oversized text;
- structurally malformed provider output.

The existing grounded validator then enforces Top order/headline locking, allowed assets/events/numbers, citations, causal and prediction guardrails, trading-language prohibition, and output length.

## Failure mapping

| Failure | Normalized fallback reason | Retry |
|---|---|---:|
| No API key | `no_provider_configured` | No request |
| Timeout | `provider_timeout` | At most once |
| Rate limit | `provider_rate_limit` | At most once |
| Network / retryable HTTP | `provider_error` | At most once |
| Non-retryable HTTP | `provider_error` | No |
| Malformed provider response | `malformed_provider_response` | No |
| Grounded validator rejection | `invalid_llm_output` | No |

All failures atomically publish the existing deterministic `daily_market_brief.md` as `ai_market_brief.md`. Workflow completion does not depend on provider availability.

## Generation metadata

Success records:

```json
{
  "generation_mode": "grounded_ai",
  "generation_status": "success",
  "provider": "openai_responses",
  "fallback_reason": null
}
```

Fallback records preserve the provider identifier when a configured provider was attempted and use the normalized reason. A missing key records `provider: null` and `fallback_reason: "no_provider_configured"`.

## Security and logging

- Credentials are read only from the process environment.
- The key is used only in the Authorization request header.
- Keys, request headers, prompts, raw responses, and provider error bodies are never written to artifacts or logs.
- Public generation metadata accepts only its frozen allowlisted fields.
- Exception messages exposed by the adapter contain normalized status categories, never response bodies.
- Tests use injected fake transports and never contact the provider.
