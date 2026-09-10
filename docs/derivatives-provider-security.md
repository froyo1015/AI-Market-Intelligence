# Phase D-0 — Provider Security Boundary

Contracts and offline security tests only. No adapter, HTTP client, credentials,
workflow, ingestion or existing production/publication path is changed.

## 1. API key lifecycle

Prefer unauthenticated public endpoints where approved. If a future provider
requires a key, an operator creates a dedicated read-only market-data credential,
without trading, withdrawal or account access. Register only its environment
variable name in a reviewed provider policy. Never put values in configuration,
fixtures, commands, URLs, git, reports or chat. Operators own expiry monitoring,
rotation and revocation. Rotate by replacing the secret and validating the next
authorized run; revoke compromised keys immediately. This implementation neither
creates keys nor automates rotation, purchases or account permissions.

## 2. GitHub Actions injection (future integration)

Use an explicitly approved repository/environment secret bound only to the
future trusted provider step via `env`, not job-wide env, CLI arguments, outputs
or generated env files. Missing credentials must become `missing_credential`,
not trigger interactive login. Do not expose secrets to fork/PR execution,
untrusted checkout code or `pull_request_target` code execution. Keep the current
workflow unchanged; no secret is configured by this phase.

GitHub documents step environment injection and limitations of secret masking;
masking is defense in depth, not permission to print credentials. Avoid shell
tracing, environment dumps and transformed secret logging. See
[GitHub's secret handling guidance](https://docs.github.com/en/actions/security-for-github-actions/security-guides/using-secrets-in-github-actions).

## 3. Runtime-only access

`EnvironmentSecretAccess` accepts an explicit allowed variable set and resolves
values lazily. It returns an opaque `RuntimeSecret`: str/repr are redacted,
pickle is forbidden and JSON serialization is unsupported. Only a scoped
`expose()` context reveals the value to a future transport implementation;
closing the context revokes the handle even after an exception. No global cache,
disk writer or secret-bearing dataclass is provided. Environment values are not
copied into provider requests or result contracts.

Python cannot reliably erase immutable strings or prevent trusted adapter code
from retaining a revealed value. This abstraction prevents accidental exposure,
not malicious in-process code, heap inspection or environment access. Do not
claim memory zeroization. Raw payload security still requires review at ingestion.

## 4. Public artifact filtering

Default deny: raw receipts, headers, endpoints, query parameters, prompts,
exceptions and internal manifests have NO public schema here. D-0 permits only
one proposed `derivatives_provider_health_v1` shape at one fixed basename,
`derivatives_provider_health.json`: schema, registered provider ID, available/
unavailable status and normalized failure code. It publishes no free-form text,
URLs, observations or source responses. Unknown/nested fields reject rather than
being silently stripped. Reject path traversal and secret value occurrences.
Accept structured dictionaries only, not untrusted serialized JSON with duplicate
keys. Future serializers must reject duplicate keys before validation.

Provider IDs are operator-reviewed safe identifiers, not remote strings. Optional
known-secret scanning is defense in depth; it cannot detect all encodings or
unregistered secrets. The closed schema is the primary control. Validation is
read-only, does not publish and does not expand existing deployment allowlists.
No derivatives artifact is approved for actual public deployment in this phase.

## 5. Provider boundary

`ProviderAdapter.collect(request, secrets)` is a Protocol, no implementation.
Request includes a registered provider ID, bounded metric/asset references and
explicit request budget. Results contain internal receipt references and typed
failure codes, never credentials or raw exception text. Public rendering must
use the closed public schema, not serialize internal results. Hosts, methods,
authentication header placement, redaction and normalization receipts must be
reviewed with a real adapter later. No arbitrary user-controlled URLs, redirect
following or credential forwarding is authorized by this interface.

## 6. Failure classification

Codes: missing_credential, authentication_failed, access_denied, rate_limited,
timeout, network_error, provider_error, invalid_response, budget_exhausted.
Unknown errors become invalid_response; no raw body/message enters logs or
public artifacts. Authentication/access failures stop that provider without
retry or fallback credentials. Transient timeout/network/provider errors may
retry once subject to remaining budget. HTTP 429 or explicit provider throttling
is rate_limited; ordinary 403 is access_denied, not assumed transient.

## 7. Rate limits

Contract caps: concurrency one (future host responsibility), one request/second,
20 total attempts including retries, 10-second request timeout, 120-second total
deadline, at most one retry. This phase validates configuration, not actual
network pacing. A future transport must enforce wall-clock/page/body budgets,
respect Retry-After and provider ceilings, open a provider circuit on throttling
and stop if reset exceeds deadline. No key rotation or proxy rotation to evade
limits. Explicit bans/access denial are not retried.

## 8. Logging restrictions and tests

Only reviewed provider IDs and typed failure enums are safe log fields. Never
log environment variables, credential handles with custom serialization, raw
requests/responses, headers, signed URLs, exception messages or request locals.
No logger or network client is introduced. Tests use obvious dummy values and
an injected mapping, not real environment secrets.

Tests cover lazy/allowlisted resolution, absent/invalid values, redaction,
serialization rejection, scope close after exceptions, request budget checks,
public closed-schema/path rejection and production isolation regressions.
Provider integration still needs a concrete transport security review. Stop here.
