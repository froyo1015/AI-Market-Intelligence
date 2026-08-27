"""Schema for Phase 6.4-B1 deterministic Markdown rendering."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DeterministicBrief:
    source_run_id: str
    report_date: str
    source_generated_at: str
    source_status: str
    markdown: str
    schema_contract: str = "deterministic_brief_renderer_v1"
