"""Run-level audit schema for deterministic intelligence orchestration."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

from src.models.freshness_schema import FRESHNESS_CONTRACT_VERSION


MODULE_STATUSES = {"success", "partial", "unavailable", "blocked", "failed"}
RUN_STATUSES = {"complete", "partial", "failed"}
FRESHNESS_STATUSES = {"current", "stale", "unavailable", "unknown"}


@dataclass
class ArtifactRunRecord:
    path: str
    artifact_type: str
    sha256: str
    versions: Dict[str, str] = field(default_factory=dict)
    source_timestamp: Optional[str] = None
    retrieved_at: Optional[str] = None
    generated_at: Optional[str] = None
    age_seconds: Optional[float] = None
    data_status: str = "success"
    freshness_status: str = "unknown"
    source_health: List[Dict[str, Any]] = field(default_factory=list)
    approved_for_publication: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ModuleRunRecord:
    sequence: int
    name: str
    hard_dependencies: List[str]
    soft_dependencies: List[str]
    started_at: str
    completed_at: str
    status: str
    source_timestamp: Optional[str]
    retrieved_at: Optional[str]
    generated_at: str
    age_seconds: Optional[float]
    freshness_status: str
    declared_artifacts: List[str]
    artifacts: List[ArtifactRunRecord] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    failure: Optional[Dict[str, Any]] = None
    generation_metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["artifacts"] = [artifact.to_dict() for artifact in self.artifacts]
        if self.generation_metadata is None:
            payload.pop("generation_metadata", None)
        return payload


@dataclass
class RunManifest:
    run_id: str
    execution_started_at: str
    execution_completed_at: str
    status: str
    source_timestamp: Optional[str]
    retrieved_at: Optional[str]
    generated_at: str
    age_seconds: Optional[float]
    freshness_status: str
    execution_order: List[str]
    modules: List[ModuleRunRecord]
    artifact_versions: Dict[str, Dict[str, str]]
    failures: List[Dict[str, Any]]
    publication: Dict[str, List[str]]
    schema_version: str = "1.0"
    artifact_type: str = "run_manifest"
    freshness_contract_version: str = FRESHNESS_CONTRACT_VERSION

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "artifact_type": self.artifact_type,
            "freshness_contract_version": self.freshness_contract_version,
            "run_id": self.run_id,
            "execution_timestamp": self.execution_started_at,
            "execution_started_at": self.execution_started_at,
            "execution_completed_at": self.execution_completed_at,
            "status": self.status,
            "source_timestamp": self.source_timestamp,
            "retrieved_at": self.retrieved_at,
            "generated_at": self.generated_at,
            "age_seconds": self.age_seconds,
            "freshness_status": self.freshness_status,
            "execution_order": list(self.execution_order),
            "modules": [module.to_dict() for module in self.modules],
            "artifact_versions": self.artifact_versions,
            "failures": self.failures,
            "publication": self.publication,
        }
