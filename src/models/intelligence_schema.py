"""Schemas for Phase 6.4-A deterministic structured intelligence."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, List


@dataclass(frozen=True)
class IntelligenceObject:
    object_id: str
    object_type: str
    source_artifact: str
    source_run_id: str
    source_generated_at: str
    validation_status: str
    data_status: str
    timestamps: Dict[str, List[str]]
    evidence_refs: Dict[str, List[str]]
    payload: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class DailyIntelligenceArtifact:
    run_id: str
    report_date: str
    generated_at: str
    status: str
    input_refs: Dict[str, str]
    data_window: Dict[str, Any]
    coverage: List[Dict[str, Any]]
    market_regime: IntelligenceObject
    cross_asset_signals: List[IntelligenceObject]
    upcoming_events: List[IntelligenceObject]
    data_quality_risks: List[IntelligenceObject]
    observed_market_stress: List[IntelligenceObject]
    provenance_catalog: Dict[str, List[Dict[str, Any]]]
    warnings: List[str]
    limitations: List[str]
    schema_version: str = "1.0"
    schema_contract: str = "daily_intelligence_v1"

    def to_dict(self) -> Dict[str, Any]:
        sections = (
            self.cross_asset_signals,
            self.upcoming_events,
            self.data_quality_risks,
            self.observed_market_stress,
        )
        return {
            "schema_version": self.schema_version,
            "artifact_type": "daily_intelligence",
            "run_id": self.run_id,
            "report_date": self.report_date,
            "generated_at": self.generated_at,
            "status": self.status,
            "composition_scope": "validated_structured_intelligence",
            "schema_contract": self.schema_contract,
            "input_refs": dict(self.input_refs),
            "data_window": dict(self.data_window),
            "coverage": [dict(item) for item in self.coverage],
            "object_counts": {
                "market_regime": 1,
                "cross_asset_signals": len(self.cross_asset_signals),
                "upcoming_events": len(self.upcoming_events),
                "data_quality_risks": len(self.data_quality_risks),
                "observed_market_stress": len(self.observed_market_stress),
                "total": 1 + sum(len(items) for items in sections),
            },
            "market_regime": self.market_regime.to_dict(),
            "cross_asset_signals": [item.to_dict() for item in self.cross_asset_signals],
            "upcoming_events": [item.to_dict() for item in self.upcoming_events],
            "data_quality_risks": [
                item.to_dict() for item in self.data_quality_risks
            ],
            "observed_market_stress": [
                item.to_dict() for item in self.observed_market_stress
            ],
            "provenance_catalog": {
                key: [dict(item) for item in value]
                for key, value in self.provenance_catalog.items()
            },
            "warnings": list(self.warnings),
            "limitations": list(self.limitations),
        }
