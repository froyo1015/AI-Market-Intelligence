"""Run-level audit schema for deterministic intelligence orchestration."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


MODULE_STATUSES = {"success", "partial", "unavailable", "blocked", "failed"}
RUN_STATUSES = {"complete", "partial", "failed"}
FRESHNESS_STATUSES = {"current", "stale", "mixed", "unknown"}


@dataclass
class ArtifactRunRecord:
    path: str
    artifact_type: str
    sha256: str
    versions: Dict[str, str] = field(default_factory=dict)
    generated_at: Optional[str] = None
    data_status: str = "success"
    freshness_status: str = "unknown"
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
    freshness_status: str
    declared_artifacts: List[str]
    artifacts: List[ArtifactRunRecord] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    failure: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["artifacts"] = [artifact.to_dict() for artifact in self.artifacts]
        return payload


@dataclass
class RunManifest:
    run_id: str
    execution_started_at: str
    execution_completed_at: str
    status: str
    freshness_status: str
    execution_order: List[str]
    modules: List[ModuleRunRecord]
    artifact_versions: Dict[str, Dict[str, str]]
    failures: List[Dict[str, Any]]
    publication: Dict[str, List[str]]
    schema_version: str = "1.0"
    artifact_type: str = "run_manifest"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "artifact_type": self.artifact_type,
            "run_id": self.run_id,
            "execution_timestamp": self.execution_started_at,
            "execution_started_at": self.execution_started_at,
            "execution_completed_at": self.execution_completed_at,
            "status": self.status,
            "freshness_status": self.freshness_status,
            "execution_order": list(self.execution_order),
            "modules": [module.to_dict() for module in self.modules],
            "artifact_versions": self.artifact_versions,
            "failures": self.failures,
            "publication": self.publication,
        }
