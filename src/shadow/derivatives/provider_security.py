"""Provider-neutral contracts only. No transport or publication implementation."""

import os
import re
from contextlib import contextmanager
from dataclasses import dataclass
from enum import Enum
from typing import Mapping, Optional, Protocol, Tuple


class SecurityBoundaryError(ValueError):
    """Messages are fixed codes, never remote or credential-bearing strings."""


class FailureCode(str, Enum):
    MISSING_CREDENTIAL = "missing_credential"
    AUTHENTICATION_FAILED = "authentication_failed"
    ACCESS_DENIED = "access_denied"
    RATE_LIMITED = "rate_limited"
    TIMEOUT = "timeout"
    NETWORK_ERROR = "network_error"
    PROVIDER_ERROR = "provider_error"
    INVALID_RESPONSE = "invalid_response"
    BUDGET_EXHAUSTED = "budget_exhausted"


class RuntimeSecret:
    __slots__ = ("__value",)

    def __init__(self, value):
        if not isinstance(value, str) or not value or any(c.isspace() or ord(c) < 32 or ord(c) == 127 for c in value):
            raise SecurityBoundaryError("invalid_credential")
        self.__value = value

    def __repr__(self):
        return "RuntimeSecret([REDACTED])"

    __str__ = __repr__

    def __reduce_ex__(self, protocol):
        raise SecurityBoundaryError("credential_serialization_forbidden")

    @contextmanager
    def expose(self):
        if self.__value is None:
            raise SecurityBoundaryError("credential_closed")
        value, self.__value = self.__value, None
        try:
            yield value
        finally:
            self.__value = None


class SecretAccess(Protocol):
    def get(self, name: str) -> Optional[RuntimeSecret]: ...


class EnvironmentSecretAccess:
    __slots__ = ("_allowed", "_environment")

    def __init__(self, allowed_names, environment: Optional[Mapping[str, str]] = None):
        names = frozenset(allowed_names)
        if not all(isinstance(n, str) and re.fullmatch(r"[A-Z][A-Z0-9_]*", n) for n in names):
            raise SecurityBoundaryError("invalid_secret_policy")
        self._allowed = names
        self._environment = os.environ if environment is None else environment

    def get(self, name):
        if name not in self._allowed:
            raise SecurityBoundaryError("secret_not_allowlisted")
        value = self._environment.get(name)
        return None if value is None or value == "" else RuntimeSecret(value)

    def __repr__(self):
        return "EnvironmentSecretAccess([REDACTED])"

    def __reduce_ex__(self, protocol):
        raise SecurityBoundaryError("credential_serialization_forbidden")


@dataclass(frozen=True)
class ProviderRequest:
    provider_id: str
    instrument_refs: Tuple[str, ...]
    metrics: Tuple[str, ...]
    max_attempts: int = 20
    max_retries: int = 1
    timeout_seconds: int = 10
    deadline_seconds: int = 120
    requests_per_second: int = 1

    def __post_init__(self):
        if not isinstance(self.provider_id, str) or not re.fullmatch(r"[a-z][a-z0-9_]{0,63}", self.provider_id):
            raise SecurityBoundaryError("invalid_provider_id")
        for value, lower, upper in ((self.max_attempts, 1, 20), (self.max_retries, 0, 1),
                                    (self.timeout_seconds, 1, 10), (self.deadline_seconds, 1, 120),
                                    (self.requests_per_second, 1, 1)):
            if type(value) is not int or not lower <= value <= upper:
                raise SecurityBoundaryError("invalid_budget")
        if self.timeout_seconds > self.deadline_seconds:
            raise SecurityBoundaryError("invalid_budget")
        if not isinstance(self.instrument_refs, tuple) or not 1 <= len(self.instrument_refs) <= 10 or not all(
                isinstance(ref, str) and re.fullmatch(r"instrument:[A-Za-z0-9:_-]+@[1-9][0-9]*", ref)
                for ref in self.instrument_refs) or len(set(self.instrument_refs)) != len(self.instrument_refs):
            raise SecurityBoundaryError("invalid_instruments")
        if not isinstance(self.metrics, tuple) or not self.metrics or not all(
                m in ("funding_rate", "open_interest") for m in self.metrics) or len(set(self.metrics)) != len(self.metrics):
            raise SecurityBoundaryError("invalid_metrics")


@dataclass(frozen=True)
class ProviderResult:
    """Internal-only result. Never serialize this as a public artifact."""
    receipt_refs: Tuple[str, ...]
    failure: Optional[FailureCode]

    def __post_init__(self):
        if self.failure is not None and not isinstance(self.failure, FailureCode):
            raise SecurityBoundaryError("invalid_failure_code")
        if not isinstance(self.receipt_refs, tuple) or not all(isinstance(r, str) and
                re.fullmatch(r"receipt:[A-Za-z0-9:_-]+", r) for r in self.receipt_refs):
            raise SecurityBoundaryError("invalid_receipt_refs")


class ProviderAdapter(Protocol):
    def collect(self, request: ProviderRequest, secrets: SecretAccess) -> ProviderResult: ...


def validate_public_artifact(filename, payload, approved_provider_ids, known_secrets=()):
    """Fail-closed health-only publication gate; does not write or sanitize."""
    if filename != "derivatives_provider_health.json":
        raise SecurityBoundaryError("artifact_not_allowlisted")
    if type(payload) is not dict or set(payload) != {"schema_contract", "provider_id", "status", "failure_code"}:
        raise SecurityBoundaryError("invalid_public_fields")
    provider = payload["provider_id"]
    if not isinstance(provider, str) or not re.fullmatch(r"[a-z][a-z0-9_]{0,63}", provider) or provider not in approved_provider_ids:
        raise SecurityBoundaryError("provider_not_allowlisted")
    if payload["schema_contract"] != "derivatives_provider_health_v1":
        raise SecurityBoundaryError("invalid_public_schema")
    failure = payload["failure_code"]
    if not ((payload["status"] == "available" and failure is None) or
            (payload["status"] == "unavailable" and type(failure) is str and failure in {c.value for c in FailureCode})):
        raise SecurityBoundaryError("invalid_public_status")
    for secret in known_secrets:
        if not isinstance(secret, str) or not secret:
            raise SecurityBoundaryError("invalid_secret_scan_policy")
        if any(secret in value for value in payload.values() if isinstance(value, str)):
            raise SecurityBoundaryError("public_secret_detected")
    return True
