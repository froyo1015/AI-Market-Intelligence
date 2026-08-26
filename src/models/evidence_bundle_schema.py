"""Schemas for the Phase 6.2-D consolidated evidence artifact."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class CoverageRecord:
    input_type: str
    artifact: str
    run_id: Optional[str]
    generated_at: Optional[str]
    status: str
    record_count: int
    stale_record_count: int
    warnings: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ConsolidationRejection:
    record_type: str
    record_id: Optional[str]
    input_artifact: str
    reason_codes: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ConsolidatedEvidenceBundle:
    id: str
    type: str
    related_assets: List[str]
    source_records: List[Dict[str, Any]]
    observations: List[Dict[str, Any]]
    events: List[Dict[str, Any]]
    evidence_records: List[Dict[str, Any]]
    timestamps: Dict[str, Any]
    verification_level: str
    data_quality: Dict[str, Any]
    freshness: Dict[str, Any]
    provenance: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ConsolidatedEvidenceArtifact:
    run_id: str
    report_date: str
    generated_at: str
    status: str
    warnings: List[str]
    coverage: List[CoverageRecord]
    bundles: List[ConsolidatedEvidenceBundle]
    rejections: List[ConsolidationRejection]
    schema_version: str = "1.0"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "artifact_type": "evidence_bundle",
            "run_id": self.run_id,
            "report_date": self.report_date,
            "generated_at": self.generated_at,
            "status": self.status,
            "warnings": list(self.warnings),
            "coverage": [item.to_dict() for item in self.coverage],
            "bundle_count": len(self.bundles),
            "rejection_count": len(self.rejections),
            "rejections": [item.to_dict() for item in self.rejections],
            "bundles": [item.to_dict() for item in self.bundles],
        }
