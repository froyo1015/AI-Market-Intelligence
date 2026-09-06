from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from src.grounded_brief.llm_adapter import (
    OpenAIResponsesConfig,
    OpenAIResponsesGroundedLLMAdapter,
    ProviderHTTPResponse,
    UnavailableGroundedLLMAdapter,
    grounded_llm_adapter_from_environment,
)
from tests.test_grounded_ai_brief import (
    _inputs,
    _run_pipeline,
    _valid_brief,
)


TEST_SECRET = "sk-test-never-publish"


class FakeTransport:
    def __init__(self, outcomes: Iterable[object]) -> None:
        self.outcomes = list(outcomes)
        self.calls: list[dict] = []

    def __call__(self, url, headers, body, timeout_seconds):
        self.calls.append(
            {
                "url": url,
                "headers": dict(headers),
                "payload": json.loads(body),
                "timeout_seconds": timeout_seconds,
            }
        )
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome


def _response(markdown: str) -> ProviderHTTPResponse:
    return ProviderHTTPResponse(
        200,
        json.dumps(
            {
                "id": "resp_test",
                "status": "completed",
                "output": [
                    {
                        "type": "message",
                        "role": "assistant",
                        "status": "completed",
                        "content": [
                            {
                                "type": "output_text",
                                "text": markdown,
                                "annotations": [],
                            }
                        ],
                    }
                ],
            }
        ).encode("utf-8"),
    )


def _adapter(
    transport: FakeTransport,
    retries: int = 1,
) -> OpenAIResponsesGroundedLLMAdapter:
    return OpenAIResponsesGroundedLLMAdapter(
        OpenAIResponsesConfig(
            api_key=TEST_SECRET,
            model="gpt-test-grounded-writer",
            timeout_seconds=12,
            max_output_tokens=1200,
            max_input_characters=200_000,
            transient_retries=retries,
        ),
        transport=transport,
        sleeper=lambda _: None,
    )


def test_successful_real_provider_style_response_uses_one_bounded_request(
    tmp_path: Path,
) -> None:
    top, daily = _inputs()
    brief = _valid_brief(top, daily)
    transport = FakeTransport([_response(brief)])

    result, output, _ = _run_pipeline(
        tmp_path,
        top,
        daily,
        _adapter(transport),
    )

    assert result.generation_mode == "grounded_ai"
    assert result.generation_status == "success"
    assert result.provider == "openai_responses"
    assert result.fallback_reason is None
    assert output.read_text(encoding="utf-8") == brief
    assert len(transport.calls) == 1
    request = transport.calls[0]
    assert request["payload"]["model"] == "gpt-test-grounded-writer"
    assert request["payload"]["max_output_tokens"] == 1200
    assert request["payload"]["tools"] == []
    assert request["payload"]["tool_choice"] == "none"
    assert request["payload"]["store"] is False
    assert request["payload"]["background"] is False
    assert request["timeout_seconds"] == 12


def test_missing_secret_selects_unavailable_adapter_without_request(
    tmp_path: Path,
) -> None:
    top, daily = _inputs()
    transport = FakeTransport([])
    adapter = grounded_llm_adapter_from_environment({}, transport=transport)

    assert isinstance(adapter, UnavailableGroundedLLMAdapter)
    result, output, fallback = _run_pipeline(
        tmp_path,
        top,
        daily,
        adapter,
    )

    assert result.provider is None
    assert result.fallback_reason == "no_provider_configured"
    assert output.read_bytes() == fallback.read_bytes()
    assert transport.calls == []


def test_environment_model_and_limits_are_configurable() -> None:
    config = OpenAIResponsesConfig.from_environment(
        {
            "OPENAI_API_KEY": TEST_SECRET,
            "OPENAI_GROUNDED_BRIEF_MODEL": "gpt-configured-writer",
            "OPENAI_GROUNDED_BRIEF_TIMEOUT_SECONDS": "18",
            "OPENAI_GROUNDED_BRIEF_MAX_OUTPUT_TOKENS": "1500",
            "OPENAI_GROUNDED_BRIEF_MAX_INPUT_CHARS": "190000",
            "OPENAI_GROUNDED_BRIEF_TRANSIENT_RETRIES": "0",
        }
    )

    assert config.model == "gpt-configured-writer"
    assert config.timeout_seconds == 18
    assert config.max_output_tokens == 1500
    assert config.max_input_characters == 190000
    assert config.transient_retries == 0
    assert TEST_SECRET not in repr(config)


def test_timeout_retries_once_then_falls_back(tmp_path: Path) -> None:
    top, daily = _inputs()
    transport = FakeTransport([TimeoutError(), TimeoutError()])
    result, output, fallback = _run_pipeline(
        tmp_path,
        top,
        daily,
        _adapter(transport),
    )

    assert len(transport.calls) == 2
    assert result.fallback_reason == "provider_timeout"
    assert output.read_bytes() == fallback.read_bytes()


def test_non_retryable_http_provider_error_does_not_retry(tmp_path: Path) -> None:
    top, daily = _inputs()
    transport = FakeTransport([ProviderHTTPResponse(400, b"secret error body")])
    result, output, fallback = _run_pipeline(
        tmp_path,
        top,
        daily,
        _adapter(transport),
    )

    assert len(transport.calls) == 1
    assert result.fallback_reason == "provider_error"
    assert "secret error body" not in (result.failure_message or "")
    assert output.read_bytes() == fallback.read_bytes()


def test_rate_limit_retries_at_most_once_and_records_normalized_reason(
    tmp_path: Path,
) -> None:
    top, daily = _inputs()
    transport = FakeTransport(
        [ProviderHTTPResponse(429, b""), ProviderHTTPResponse(429, b"")]
    )
    result, _, _ = _run_pipeline(
        tmp_path,
        top,
        daily,
        _adapter(transport),
    )

    assert len(transport.calls) == 2
    assert result.fallback_reason == "provider_rate_limit"


def test_malformed_response_does_not_retry_and_falls_back(tmp_path: Path) -> None:
    top, daily = _inputs()
    transport = FakeTransport([ProviderHTTPResponse(200, b"not-json")])
    result, output, fallback = _run_pipeline(
        tmp_path,
        top,
        daily,
        _adapter(transport),
    )

    assert len(transport.calls) == 1
    assert result.fallback_reason == "malformed_provider_response"
    assert output.read_bytes() == fallback.read_bytes()


def test_retryable_network_failure_can_recover_on_second_request(
    tmp_path: Path,
) -> None:
    top, daily = _inputs()
    brief = _valid_brief(top, daily)
    transport = FakeTransport([OSError("network unavailable"), _response(brief)])
    result, output, _ = _run_pipeline(
        tmp_path,
        top,
        daily,
        _adapter(transport),
    )

    assert len(transport.calls) == 2
    assert result.generation_mode == "grounded_ai"
    assert output.read_text(encoding="utf-8") == brief


def test_validator_rejection_never_triggers_provider_retry(tmp_path: Path) -> None:
    top, daily = _inputs()
    invalid = "# Daily Market Intelligence Brief\n\nGold will rise.\n"
    transport = FakeTransport([_response(invalid), _response(_valid_brief(top, daily))])
    result, output, fallback = _run_pipeline(
        tmp_path,
        top,
        daily,
        _adapter(transport),
    )

    assert len(transport.calls) == 1
    assert result.fallback_reason == "invalid_llm_output"
    assert output.read_bytes() == fallback.read_bytes()


def test_input_cost_ceiling_prevents_provider_request(tmp_path: Path) -> None:
    top, daily = _inputs()
    transport = FakeTransport([])
    adapter = OpenAIResponsesGroundedLLMAdapter(
        OpenAIResponsesConfig(
            api_key=TEST_SECRET,
            model="gpt-test-grounded-writer",
            max_input_characters=10_000,
        ),
        transport=transport,
    )
    result, output, fallback = _run_pipeline(
        tmp_path,
        top,
        daily,
        adapter,
    )

    assert transport.calls == []
    assert result.fallback_reason == "provider_error"
    assert output.read_bytes() == fallback.read_bytes()


def test_secret_is_not_exposed_in_metadata_failure_or_artifacts(
    tmp_path: Path,
) -> None:
    top, daily = _inputs()
    transport = FakeTransport([ProviderHTTPResponse(500, TEST_SECRET.encode())] * 2)
    result, output, fallback = _run_pipeline(
        tmp_path,
        top,
        daily,
        _adapter(transport),
    )

    public_values = json.dumps(result.generation_metadata())
    diagnostic_values = json.dumps(result.to_dict())
    assert TEST_SECRET not in public_values
    assert TEST_SECRET not in diagnostic_values
    assert TEST_SECRET not in output.read_text(encoding="utf-8")
    assert output.read_bytes() == fallback.read_bytes()
    assert len(transport.calls) == 2


def test_workflow_reads_secret_without_embedding_credentials() -> None:
    workflow = Path(".github/workflows/daily_market_brief.yml").read_text(
        encoding="utf-8"
    )

    assert "OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}" in workflow
    assert "OPENAI_GROUNDED_BRIEF_MODEL" in workflow
    assert TEST_SECRET not in workflow
    assert "sk-" not in workflow
