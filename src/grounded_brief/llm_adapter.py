"""Provider-neutral boundary and bounded OpenAI Responses implementation."""

from __future__ import annotations

import json
import os
import socket
import time
from dataclasses import dataclass, field
from typing import Callable, Mapping, Optional, Protocol
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


OPENAI_RESPONSES_URL = "https://api.openai.com/v1/responses"
DEFAULT_OPENAI_MODEL = "gpt-5.6-luna"
DEFAULT_TIMEOUT_SECONDS = 30.0
DEFAULT_MAX_OUTPUT_TOKENS = 2400
DEFAULT_MAX_INPUT_CHARACTERS = 200_000
DEFAULT_TRANSIENT_RETRIES = 1
MAX_RESPONSE_BYTES = 1_000_000


class GroundedLLMAdapterError(RuntimeError):
    """Raised when a writing provider cannot return usable Markdown."""

    fallback_reason = "provider_error"
    retryable = False


class GroundedLLMAdapter(Protocol):
    provider_name: str

    def generate(self, prompt: str) -> str:
        """Return Markdown generated only from the supplied grounded prompt."""


class UnavailableGroundedLLMAdapter:
    """Explicit no-provider adapter used to exercise the production fallback."""

    provider_name = "unconfigured"

    def generate(self, prompt: str) -> str:
        del prompt
        raise GroundedLLMAdapterError("no grounded LLM provider is configured")


class OpenAIProviderError(GroundedLLMAdapterError):
    """Safe provider failure that never includes a response body or secret."""


class OpenAIProviderTimeoutError(OpenAIProviderError, TimeoutError):
    fallback_reason = "provider_timeout"
    retryable = True


class OpenAIProviderNetworkError(OpenAIProviderError):
    retryable = True


class OpenAIRateLimitError(OpenAIProviderError):
    fallback_reason = "provider_rate_limit"
    retryable = True


class OpenAIMalformedResponseError(OpenAIProviderError):
    fallback_reason = "malformed_provider_response"


class OpenAIConfigurationError(OpenAIProviderError):
    """Raised inside the adapter so invalid config falls back safely."""


@dataclass(frozen=True)
class ProviderHTTPResponse:
    status_code: int
    body: bytes


class ProviderHTTPTransport(Protocol):
    def __call__(
        self,
        url: str,
        headers: Mapping[str, str],
        body: bytes,
        timeout_seconds: float,
    ) -> ProviderHTTPResponse:
        """Send one provider request and return a bounded response."""


@dataclass(frozen=True)
class OpenAIResponsesConfig:
    api_key: str = field(repr=False)
    model: str = DEFAULT_OPENAI_MODEL
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS
    max_output_tokens: int = DEFAULT_MAX_OUTPUT_TOKENS
    max_input_characters: int = DEFAULT_MAX_INPUT_CHARACTERS
    transient_retries: int = DEFAULT_TRANSIENT_RETRIES

    @classmethod
    def from_environment(
        cls,
        environment: Mapping[str, str],
    ) -> "OpenAIResponsesConfig":
        key = environment.get("OPENAI_API_KEY", "").strip()
        if not key:
            raise OpenAIConfigurationError("provider credential is unavailable")
        model = environment.get(
            "OPENAI_GROUNDED_BRIEF_MODEL",
            DEFAULT_OPENAI_MODEL,
        ).strip()
        if not model or len(model) > 100:
            raise OpenAIConfigurationError("provider model configuration is invalid")
        timeout = _bounded_float(
            environment,
            "OPENAI_GROUNDED_BRIEF_TIMEOUT_SECONDS",
            DEFAULT_TIMEOUT_SECONDS,
            5.0,
            120.0,
        )
        output_tokens = _bounded_int(
            environment,
            "OPENAI_GROUNDED_BRIEF_MAX_OUTPUT_TOKENS",
            DEFAULT_MAX_OUTPUT_TOKENS,
            256,
            4096,
        )
        input_characters = _bounded_int(
            environment,
            "OPENAI_GROUNDED_BRIEF_MAX_INPUT_CHARS",
            DEFAULT_MAX_INPUT_CHARACTERS,
            10_000,
            500_000,
        )
        retries = _bounded_int(
            environment,
            "OPENAI_GROUNDED_BRIEF_TRANSIENT_RETRIES",
            DEFAULT_TRANSIENT_RETRIES,
            0,
            1,
        )
        return cls(
            api_key=key,
            model=model,
            timeout_seconds=timeout,
            max_output_tokens=output_tokens,
            max_input_characters=input_characters,
            transient_retries=retries,
        )


class OpenAIResponsesGroundedLLMAdapter:
    """Single-turn, no-tools Responses API writer with bounded retry."""

    provider_name = "openai_responses"

    def __init__(
        self,
        config: OpenAIResponsesConfig,
        transport: ProviderHTTPTransport = None,
        sleeper: Callable[[float], None] = time.sleep,
    ) -> None:
        self._config = config
        self._transport = transport or _urllib_transport
        self._sleeper = sleeper

    def generate(self, prompt: str) -> str:
        if not isinstance(prompt, str) or not prompt.strip():
            raise OpenAIConfigurationError("grounded prompt is empty")
        if len(prompt) > self._config.max_input_characters:
            raise OpenAIConfigurationError("grounded prompt exceeds input limit")

        attempts = self._config.transient_retries + 1
        for attempt in range(attempts):
            try:
                return self._generate_once(prompt)
            except OpenAIProviderError as exc:
                if not exc.retryable or attempt + 1 >= attempts:
                    raise
                self._sleeper(0.25)
        raise OpenAIProviderError("provider attempt budget exhausted")

    def _generate_once(self, prompt: str) -> str:
        payload = {
            "model": self._config.model,
            "input": prompt,
            "max_output_tokens": self._config.max_output_tokens,
            "store": False,
            "background": False,
            "tools": [],
            "tool_choice": "none",
            "parallel_tool_calls": False,
            "truncation": "disabled",
            "text": {"format": {"type": "text"}},
        }
        headers = {
            "Authorization": "Bearer " + self._config.api_key,
            "Content-Type": "application/json",
        }
        try:
            response = self._transport(
                OPENAI_RESPONSES_URL,
                headers,
                json.dumps(payload, separators=(",", ":")).encode("utf-8"),
                self._config.timeout_seconds,
            )
        except OpenAIProviderError:
            raise
        except (TimeoutError, socket.timeout) as exc:
            raise OpenAIProviderTimeoutError("provider request timed out") from exc
        except (OSError, URLError) as exc:
            raise OpenAIProviderNetworkError("provider network request failed") from exc

        _raise_for_status(response.status_code)
        if len(response.body) > MAX_RESPONSE_BYTES:
            raise OpenAIMalformedResponseError("provider response exceeds size limit")
        try:
            decoded = json.loads(response.body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise OpenAIMalformedResponseError("provider response is malformed") from exc
        return _extract_output_text(decoded)


class InvalidOpenAIConfigurationAdapter:
    """Configured provider identity that fails safely inside the pipeline."""

    provider_name = "openai_responses"

    def generate(self, prompt: str) -> str:
        del prompt
        raise OpenAIConfigurationError("provider configuration is invalid")


def grounded_llm_adapter_from_environment(
    environment: Optional[Mapping[str, str]] = None,
    transport: ProviderHTTPTransport = None,
) -> GroundedLLMAdapter:
    values = environment if environment is not None else os.environ
    if not values.get("OPENAI_API_KEY", "").strip():
        return UnavailableGroundedLLMAdapter()
    try:
        config = OpenAIResponsesConfig.from_environment(values)
    except OpenAIConfigurationError:
        return InvalidOpenAIConfigurationAdapter()
    return OpenAIResponsesGroundedLLMAdapter(config, transport=transport)


def _urllib_transport(
    url: str,
    headers: Mapping[str, str],
    body: bytes,
    timeout_seconds: float,
) -> ProviderHTTPResponse:
    request = Request(url, data=body, headers=dict(headers), method="POST")
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            content = response.read(MAX_RESPONSE_BYTES + 1)
            return ProviderHTTPResponse(int(response.status), content)
    except HTTPError as exc:
        return ProviderHTTPResponse(int(exc.code), b"")
    except (TimeoutError, socket.timeout) as exc:
        raise OpenAIProviderTimeoutError("provider request timed out") from exc
    except URLError as exc:
        raise OpenAIProviderNetworkError("provider network request failed") from exc


def _raise_for_status(status_code: int) -> None:
    if 200 <= status_code < 300:
        return
    if status_code == 429:
        raise OpenAIRateLimitError("provider rate limit")
    error = OpenAIProviderError(f"provider HTTP status {status_code}")
    if status_code in {408, 409} or 500 <= status_code < 600:
        error.retryable = True
    raise error


def _extract_output_text(payload: object) -> str:
    if not isinstance(payload, dict) or payload.get("status") != "completed":
        raise OpenAIMalformedResponseError("provider response is incomplete")
    direct = payload.get("output_text")
    if isinstance(direct, str) and direct.strip():
        return _bounded_output(direct)

    texts = []
    output = payload.get("output")
    if not isinstance(output, list):
        raise OpenAIMalformedResponseError("provider output is missing")
    prohibited_types = {
        "function_call", "web_search_call", "file_search_call",
        "computer_call", "code_interpreter_call", "mcp_call",
    }
    for item in output:
        if not isinstance(item, dict):
            raise OpenAIMalformedResponseError("provider output item is malformed")
        if item.get("type") in prohibited_types:
            raise OpenAIMalformedResponseError("provider returned a tool call")
        if item.get("type") != "message":
            continue
        content = item.get("content")
        if not isinstance(content, list):
            raise OpenAIMalformedResponseError("provider message content is malformed")
        for part in content:
            if isinstance(part, dict) and part.get("type") == "output_text":
                value = part.get("text")
                if isinstance(value, str):
                    texts.append(value)
    combined = "".join(texts)
    if not combined.strip():
        raise OpenAIMalformedResponseError("provider output text is empty")
    return _bounded_output(combined)


def _bounded_output(value: str) -> str:
    if len(value) > 20_000:
        raise OpenAIMalformedResponseError("provider output exceeds character limit")
    return value


def _bounded_int(
    environment: Mapping[str, str],
    name: str,
    default: int,
    minimum: int,
    maximum: int,
) -> int:
    try:
        value = int(environment.get(name, str(default)))
    except (TypeError, ValueError) as exc:
        raise OpenAIConfigurationError(f"{name} is invalid") from exc
    if value < minimum or value > maximum:
        raise OpenAIConfigurationError(f"{name} is outside the allowed range")
    return value


def _bounded_float(
    environment: Mapping[str, str],
    name: str,
    default: float,
    minimum: float,
    maximum: float,
) -> float:
    try:
        value = float(environment.get(name, str(default)))
    except (TypeError, ValueError) as exc:
        raise OpenAIConfigurationError(f"{name} is invalid") from exc
    if value < minimum or value > maximum:
        raise OpenAIConfigurationError(f"{name} is outside the allowed range")
    return value
