"""Schemas for Phase 6.3-C observable risk conditions."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, List


@dataclass(frozen=True)
class RiskItem:
    risk_id: str
    rule_id: str
    category: str
    status: str
    attention_level: str
    title: str
    description: str
    related_assets: List[str]
    time_window: Dict[str, Any]
    observed_facts: Dict[str, Any]
    evidence_refs: Dict[str, List[str]]
    verification: Dict[str, Any]
    limitations: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RiskMonitorArtifact:
    run_id: str
    report_date: str
    generated_at: str
    status: str
    input_refs: Dict[str, str]
    input_freshness: Dict[str, Any]
    risks: List[RiskItem]
    warnings: List[str]
    limitations: List[str]
    schema_version: str = "1.0"
    rule_set_version: str = "risk_monitor_rules_v1"

    def to_dict(self) -> Dict[str, Any]:
        category_counts = {
            category: sum(item.category == category for item in self.risks)
            for category in ("upcoming_event", "data_quality", "market_stress")
        }
        return {
            "schema_version": self.schema_version,
            "artifact_type": "risk_monitor",
            "run_id": self.run_id,
            "report_date": self.report_date,
            "generated_at": self.generated_at,
            "status": self.status,
            "monitor_scope": "observable_risk_conditions",
            "rule_set_version": self.rule_set_version,
            "input_refs": dict(self.input_refs),
            "input_freshness": dict(self.input_freshness),
            "risk_count": len(self.risks),
            "category_counts": category_counts,
            "risks": [item.to_dict() for item in self.risks],
            "warnings": list(self.warnings),
            "limitations": list(self.limitations),
        }
