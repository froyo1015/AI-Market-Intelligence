"""Non-synthetic observation contracts; no production pipeline registration."""

from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class ProductionObservation:
    schema_contract: str
    synthetic: bool
    observation_id: str
    version: int
    instrument_ref: str
    receipt_ref: str
    pointers: Dict[str, str]
    metric: str
    value: str
    unit: str
    native_timestamp: int
    native_time_unit: str
    source_timestamp: str
    retrieved_at: str
    generated_at: str
    known_at: str
    freshness: Dict[str, Any]
    evidence_quality: Dict[str, Any]
    content_hash: str

    def to_dict(self):
        return asdict(self)


@dataclass(frozen=True)
class InstrumentRevision:
    instrument_id: str
    version: int
    metadata_receipt_ref: str
    definition_pointer: str
    definition: Dict[str, Any]
    content_hash: str


@dataclass(frozen=True)
class ShadowObservationOutput:
    schema_contract: str
    synthetic: bool
    run_id: str
    requested_cutoff: str
    evaluation_cutoff: str
    replay_mode: str
    sources: List[Dict[str, Any]]
    receipts: List[Dict[str, Any]]
    instruments: List[Dict[str, Any]]
    observations: List[Dict[str, Any]]
    coverage: List[Dict[str, Any]]

    def to_dict(self):
        return asdict(self)


@dataclass(frozen=True)
class ProductionValidationResult:
    errors: List[str]
    availability: str
    historical_availability: str
    output_hash: Optional[str]

    @property
    def valid(self):
        return not self.errors
