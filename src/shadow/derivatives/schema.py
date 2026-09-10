"""Shadow-only V2 schema models; validate_artifact is the trust boundary."""

from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class Asset:
    asset_id: str
    asset_class: str
    symbol: str
    identifiers: Dict[str, str]


@dataclass(frozen=True)
class Venue:
    venue_id: str
    name: str


@dataclass(frozen=True)
class Instrument:
    instrument_id: str
    version: int
    venue_ref: str
    instrument_type: str
    base_asset_ref: str
    quote_asset_ref: str
    settlement_asset_ref: str
    underlying_asset_ref: Optional[str]
    contract: Optional[Dict[str, Any]]
    token: Optional[Dict[str, Any]]


@dataclass(frozen=True)
class Source:
    source_id: str
    version: int
    venue_ref: str
    publisher: str
    definition_version: str
    retrieved_at: str
    data_reliability: Optional[float]
    raw_locator: str
    raw_payload: Dict[str, Any]
    raw_hash: str


@dataclass(frozen=True)
class DerivativesObservationV2:
    schema_contract: str
    record_id: str
    record_version: int
    instrument_ref: str
    related_assets: List[str]
    source_refs: List[str]
    observation_refs: List[str]
    payload: Dict[str, Any]
    timestamps: Dict[str, Any]
    freshness: Dict[str, Any]
    evidence_quality: Dict[str, Any]
    known_at: str
    content_hash: str

    def to_dict(self):
        return asdict(self)


@dataclass(frozen=True)
class DerivativesEvidenceV2(DerivativesObservationV2):
    claim_type: str


@dataclass(frozen=True)
class ValidationResult:
    errors: List[str]
    audit: Dict[str, Any]

    @property
    def valid(self):
        return not self.errors
