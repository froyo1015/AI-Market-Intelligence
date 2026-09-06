"""Generate a grounded AI brief or atomically fall back to deterministic text."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Sequence

from src.grounded_brief.llm_adapter import (
    GroundedLLMAdapter,
    UnavailableGroundedLLMAdapter,
    grounded_llm_adapter_from_environment,
)
from src.grounded_brief.prompt_builder import build_grounded_brief_prompt
from src.grounded_brief.validator import (
    GroundedBriefValidationError,
    validate_grounded_brief,
)
from src.models.generation_metadata_schema import GenerationMetadata


OUTPUT_DIRECTORY = Path(__file__).resolve().parents[1] / "output"
DEFAULT_TOP_PATH = OUTPUT_DIRECTORY / "top_intelligence.json"
DEFAULT_DAILY_PATH = OUTPUT_DIRECTORY / "daily_intelligence.json"
DEFAULT_FALLBACK_PATH = OUTPUT_DIRECTORY / "daily_market_brief.md"
DEFAULT_OUTPUT_PATH = OUTPUT_DIRECTORY / "ai_market_brief.md"


class GroundedBriefInputError(ValueError):
    """Raised when canonical input or deterministic fallback is invalid."""


@dataclass(frozen=True)
class GroundedBriefRunResult:
    generation_mode: str
    generation_status: str
    generated_at: str
    freshness_status: str
    validation_status: str
    provider: Optional[str]
    fallback_reason: Optional[str]
    output_path: str
    failure_type: Optional[str] = None
    failure_message: Optional[str] = None

    @property
    def mode(self) -> str:
        """Backward-compatible internal label for Phase 7.2-B callers."""
        return "generated" if self.generation_mode == "grounded_ai" else "fallback"

    def generation_metadata(self) -> Dict[str, Any]:
        return GenerationMetadata(
            generation_mode=self.generation_mode,
            generation_status=self.generation_status,
            generated_at=self.generated_at,
            freshness_status=self.freshness_status,
            validation_status=self.validation_status,
            provider=self.provider,
            fallback_reason=self.fallback_reason,
        ).to_dict()

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["mode"] = self.mode
        return payload


def run_grounded_brief_pipeline(
    top_path: Path = DEFAULT_TOP_PATH,
    daily_path: Path = DEFAULT_DAILY_PATH,
    fallback_path: Path = DEFAULT_FALLBACK_PATH,
    output_path: Path = DEFAULT_OUTPUT_PATH,
    adapter: Optional[GroundedLLMAdapter] = None,
) -> GroundedBriefRunResult:
    top = _load_json(top_path, "top_intelligence")
    daily = _load_json(daily_path, "daily_intelligence")
    fallback = _load_fallback(fallback_path)
    prompt = build_grounded_brief_prompt(top, daily)
    provider = adapter or grounded_llm_adapter_from_environment()
    provider_identifier = _provider_identifier(provider)
    freshness_status = _input_freshness(daily)

    try:
        generated = provider.generate(prompt)
        validate_grounded_brief(generated, top, daily)
    except Exception as exc:  # provider/validator isolation is the product contract
        _atomic_write(fallback, output_path)
        return GroundedBriefRunResult(
            generation_mode="deterministic_fallback",
            generation_status="fallback",
            generated_at=_utc_now(),
            freshness_status=freshness_status,
            validation_status="validated",
            provider=provider_identifier,
            fallback_reason=_fallback_reason(exc, provider_identifier),
            output_path=str(output_path),
            failure_type=type(exc).__name__,
            failure_message=_safe_message(exc),
        )

    _atomic_write(generated.rstrip() + "\n", output_path)
    return GroundedBriefRunResult(
        generation_mode="grounded_ai",
        generation_status="success",
        generated_at=_utc_now(),
        freshness_status=freshness_status,
        validation_status="validated",
        provider=provider_identifier,
        fallback_reason=None,
        output_path=str(output_path),
    )


def _load_json(path: Path, expected_type: str) -> Dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise GroundedBriefInputError(f"cannot read {expected_type}: {exc}") from exc
    if not isinstance(payload, dict) or payload.get("artifact_type") != expected_type:
        raise GroundedBriefInputError(f"expected {expected_type} artifact")
    return payload


def _load_fallback(path: Path) -> str:
    try:
        value = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise GroundedBriefInputError(f"cannot read deterministic fallback: {exc}") from exc
    if not value.strip() or not value.startswith("# Daily Market Intelligence Brief"):
        raise GroundedBriefInputError("deterministic fallback is invalid")
    return value


def _atomic_write(value: str, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(f"{path.suffix}.tmp")
    temporary.write_text(value, encoding="utf-8")
    temporary.replace(path)


def _safe_message(exc: Exception) -> str:
    text = " ".join(str(exc).split())
    return text[:300] or type(exc).__name__


def _provider_identifier(provider: GroundedLLMAdapter) -> Optional[str]:
    name = getattr(provider, "provider_name", None)
    if isinstance(provider, UnavailableGroundedLLMAdapter):
        return None
    if not isinstance(name, str) or not name.strip() or name == "unconfigured":
        return None
    return name.strip()


def _input_freshness(daily: Dict[str, Any]) -> str:
    value = daily.get("freshness_status")
    if value in {"current", "stale", "unavailable", "unknown"}:
        return str(value)
    return "unknown"


def _fallback_reason(exc: Exception, provider: Optional[str]) -> str:
    if provider is None:
        return "no_provider_configured"
    if isinstance(exc, GroundedBriefValidationError):
        return "invalid_llm_output"
    normalized = f"{type(exc).__name__} {exc}".lower()
    if isinstance(exc, TimeoutError) or "timeout" in normalized or "timed out" in normalized:
        return "provider_timeout"
    declared = getattr(exc, "fallback_reason", None)
    if declared in {
        "provider_timeout",
        "provider_rate_limit",
        "malformed_provider_response",
        "provider_error",
    }:
        return str(declared)
    return "provider_error"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate a grounded AI market brief with safe fallback."
    )
    parser.add_argument("--top", type=Path, default=DEFAULT_TOP_PATH)
    parser.add_argument("--daily", type=Path, default=DEFAULT_DAILY_PATH)
    parser.add_argument("--fallback", type=Path, default=DEFAULT_FALLBACK_PATH)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    args = parser.parse_args(argv)
    try:
        result = run_grounded_brief_pipeline(
            args.top,
            args.daily,
            args.fallback,
            args.output,
        )
    except GroundedBriefInputError as exc:
        print(f"Grounded brief failed: {exc}")
        return 1
    print(
        f"Wrote grounded brief to {args.output}; mode={result.mode}; "
        f"provider={result.provider}"
    )
    return 0


def cli() -> None:
    raise SystemExit(main())


if __name__ == "__main__":
    cli()
