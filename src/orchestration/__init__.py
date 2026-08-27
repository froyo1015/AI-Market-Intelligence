"""Phase 6.4-D deterministic daily pipeline orchestration."""

from __future__ import annotations

from typing import Any


def run_daily_orchestration(*args: Any, **kwargs: Any) -> Any:
    """Lazily load the pipeline so ``python -m`` has no import-order warning."""
    from src.orchestration.pipeline import run_daily_orchestration as run

    return run(*args, **kwargs)


__all__ = ["run_daily_orchestration"]
