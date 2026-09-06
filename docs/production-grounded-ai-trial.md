# Production Grounded AI Trial

## Scope

Phase 7.5-A activates the existing grounded writer as a monitored production
trial. It does not change prompts, grounding rules, intelligence, ranking, or
presentation. The trial uses the existing OpenAI Responses adapter and the
existing deterministic fallback.

## Activation contract

GitHub Actions reads `OPENAI_API_KEY` only from the repository secret with the
same name. The key is never accepted from a committed file, repository
variable, command-line argument, artifact, or generated page.

The production model is selected by the non-secret repository variable
`OPENAI_GROUNDED_BRIEF_MODEL`; if absent, the current configured default is
`gpt-5.6-luna`.

Activation requires:

1. deploy the current provider, evaluation, and monitoring code;
2. add the repository secret `OPENAI_API_KEY` in GitHub settings;
3. optionally set `OPENAI_GROUNDED_BRIEF_MODEL`;
4. run `Daily Market Brief` with `workflow_dispatch`;
5. inspect the workflow summary, `run_manifest.json`, and
   `ai_brief_evaluation.json`.

Secret absence is not an error. It deterministically selects fallback and is
reported as `no_provider_configured`.

## Request and cost boundary

The production workflow sets `OPENAI_GROUNDED_BRIEF_TRANSIENT_RETRIES=0` during
the trial. Therefore each scheduled or manually dispatched run can make at most
one provider request. There is no repair call, follow-up call, agent loop,
browsing, or tool call.

Existing limits remain:

- 30-second timeout;
- 2,400 maximum output tokens;
- 200,000-character maximum grounded prompt;
- one daily scheduled workflow cadence;
- deterministic fallback for every provider or validation failure.

## Monitoring states

The production monitor reads only validated `run_manifest.json` and
`ai_brief_evaluation.json`.

| State | Meaning |
| --- | --- |
| `grounded_ai_validated` | Provider output passed the existing grounding validator and the calibrated grounded evaluation profile. |
| `fallback_active` | The deterministic fallback was published and passed the calibrated fallback profile. |

The workflow summary exposes only approved generation/evaluation metadata. It
does not expose prompts, provider responses, API keys, request headers, or raw
exceptions.

## Trial acceptance

A real AI trial is accepted only when all of the following are true:

- generation mode is `grounded_ai`;
- generation status is `success`;
- provider is `openai_responses`;
- validation status is `validated`;
- evaluation mode/profile are grounded AI;
- evaluation status and validation result pass;
- grounding compliance and reference integrity pass;
- no fallback reason is recorded.

Fallback remains a successful production outcome but does not count as a real
AI trial result. Provider or validation failure is visible through normalized
metadata and must not interrupt deterministic publication.

## Current activation blocker

As of the Phase 7.5-A local readiness check, the GitHub repository does not have
an `OPENAI_API_KEY` secret and the local environment does not expose one. The
trial code can be validated with injected provider-style responses, but a live
provider result cannot be claimed until an authorized key is configured and a
deployed workflow run records `grounded_ai_validated`.
