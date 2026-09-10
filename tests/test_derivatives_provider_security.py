"""Security boundary tests use dummy credentials, never real environment values."""

import json
import pickle

import pytest

from src.shadow.derivatives.provider_security import (
    EnvironmentSecretAccess, RuntimeSecret, SecurityBoundaryError, ProviderRequest,
    ProviderResult, FailureCode, validate_public_artifact,
)


def test_lazy_access_and_rotation():
    environment = {}
    access = EnvironmentSecretAccess({"TEST_KEY"}, environment)
    assert access.get("TEST_KEY") is None
    environment["TEST_KEY"] = "dummy-test-value"
    secret = access.get("TEST_KEY")
    assert "dummy" not in repr(secret) and "dummy" not in repr(access)
    with secret.expose() as value:
        assert value == "dummy-test-value"
    with pytest.raises(SecurityBoundaryError, match="credential_closed"):
        with secret.expose():
            pass
    environment["TEST_KEY"] = "rotated-dummy"
    with access.get("TEST_KEY").expose() as value:
        assert value == "rotated-dummy"


def test_scope_exception_and_serialization(capsys):
    secret = RuntimeSecret("dummy-only")
    with pytest.raises(SecurityBoundaryError):
        pickle.dumps(secret)
    with pytest.raises(TypeError):
        json.dumps(secret)
    with pytest.raises(RuntimeError):
        with secret.expose():
            raise RuntimeError("fixed_failure")
    with pytest.raises(SecurityBoundaryError):
        with secret.expose():
            pass
    print(secret)
    assert "dummy-only" not in capsys.readouterr().out


@pytest.mark.parametrize("value", ["bad\nheader", "bad\rheader", "bad value", "\x00", 42])
def test_invalid_credentials_safe_error(value):
    with pytest.raises(SecurityBoundaryError) as exc:
        EnvironmentSecretAccess({"TEST_KEY"}, {"TEST_KEY": value}).get("TEST_KEY")
    assert str(exc.value) == "invalid_credential"


def test_allowlist_and_empty():
    access = EnvironmentSecretAccess({"TEST_KEY"}, {"TEST_KEY": "", "OTHER": "dummy"})
    assert access.get("TEST_KEY") is None
    with pytest.raises(SecurityBoundaryError):
        access.get("OTHER")


def test_access_serialization_and_nested_exposure():
    access = EnvironmentSecretAccess({"TEST_KEY"}, {"TEST_KEY": "dummy"})
    with pytest.raises(SecurityBoundaryError):
        pickle.dumps(access)
    secret = access.get("TEST_KEY")
    with secret.expose():
        with pytest.raises(SecurityBoundaryError):
            with secret.expose():
                pass


@pytest.mark.parametrize("kwargs", [{"max_attempts": 21}, {"max_retries": 2},
                                    {"timeout_seconds": 11}, {"deadline_seconds": 121},
                                    {"requests_per_second": 2}, {"max_attempts": True},
                                    {"deadline_seconds": 1}])
def test_budget_rejected(kwargs):
    with pytest.raises(SecurityBoundaryError):
        ProviderRequest("example", ("instrument:btc@1",), ("funding_rate",), **kwargs)


def test_interfaces():
    request = ProviderRequest("example", ("instrument:btc@1",), ("open_interest",))
    assert request.max_retries == 1
    assert ProviderResult((), FailureCode.MISSING_CREDENTIAL).failure == FailureCode.MISSING_CREDENTIAL
    with pytest.raises(SecurityBoundaryError):
        ProviderResult((), "raw provider error dummy-secret")


def public():
    return {"schema_contract": "derivatives_provider_health_v1", "provider_id": "example",
            "status": "available", "failure_code": None}


def test_public_health_success_and_failure():
    assert validate_public_artifact("derivatives_provider_health.json", public(), {"example"})
    p = public()
    p.update(status="unavailable", failure_code="rate_limited")
    assert validate_public_artifact("derivatives_provider_health.json", p, {"example"})


@pytest.mark.parametrize("field", ["api_key", "headers", "raw_payload", "prompt", "url", "exception", "nested"])
def test_public_extra_fields_rejected(field):
    p = public()
    p[field] = {"value": "dummy-secret"}
    with pytest.raises(SecurityBoundaryError):
        validate_public_artifact("derivatives_provider_health.json", p, {"example"})


@pytest.mark.parametrize("filename", ["../derivatives_provider_health.json", "raw.json", "run_manifest.json",
                                      "/derivatives_provider_health.json"])
def test_public_path_denied(filename):
    with pytest.raises(SecurityBoundaryError):
        validate_public_artifact(filename, public(), {"example"})


def test_secret_scan_and_provider_allowlist():
    with pytest.raises(SecurityBoundaryError, match="public_secret_detected"):
        validate_public_artifact("derivatives_provider_health.json", public(), {"example"}, ["example"])
    with pytest.raises(SecurityBoundaryError):
        validate_public_artifact("derivatives_provider_health.json", public(), {"other"})
    p = public()
    p.update(status="unavailable", failure_code="dummy-secret-error")
    with pytest.raises(SecurityBoundaryError) as exc:
        validate_public_artifact("derivatives_provider_health.json", p, {"example"})
    assert "dummy-secret" not in str(exc.value)
