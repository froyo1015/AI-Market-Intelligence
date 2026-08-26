"""Deterministic Federal Reserve NewsItem to canonical event normalization."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from src.evidence.schema import SourceReference
from src.models.event_schema import (
    EventNormalization,
    NormalizationRejection,
    NormalizedNewsEvent,
)


RULE_VERSION = "news_normalization_v1"
DEDUPE_RULE_ID = "headline_token_jaccard_0_90_v1"
DEDUPE_THRESHOLD = 0.90
DEDUPE_WINDOW_HOURS = 12
EVENT_KEY_FIELDS = ["event_type", "entity_ids", "normalized_action"]
BASE_MAPPING_RULES = ["federal_reserve_entity_v1"]
STOP_WORDS = {
    "a",
    "an",
    "and",
    "by",
    "for",
    "from",
    "in",
    "of",
    "on",
    "the",
    "to",
    "with",
}
CAUSAL_LANGUAGE = re.compile(
    r"\b(?:because|caused|causes|due to|led to|driven by)\b|"
    r"因為|由於|導致|造成|驅動",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class HeadlineClassification:
    event_type: str
    normalized_action: str
    topics: Tuple[str, ...]
    entity_ids: Tuple[str, ...]
    mapping_rule_id: str
    extraction_quality_score: float
    mapping_quality_score: float


@dataclass(frozen=True)
class EventCandidate:
    item: Dict[str, Any]
    classification: HeadlineClassification
    published_at: datetime
    title_tokens: frozenset[str]


def normalize_news_items(
    items: Iterable[Dict[str, Any]],
    generated_at: str,
) -> Tuple[List[NormalizedNewsEvent], List[NormalizationRejection]]:
    """Normalize accepted source items without sentiment or impact inference."""
    candidates: List[EventCandidate] = []
    rejections: List[NormalizationRejection] = []

    for item in items:
        item_id = str(item.get("item_id", ""))
        headline = str(item.get("headline", ""))
        if CAUSAL_LANGUAGE.search(headline):
            rejections.append(
                NormalizationRejection(
                    item_id=item_id,
                    reason_codes=["prohibited_causal_language"],
                )
            )
            continue
        classification = classify_headline(headline)
        if classification is None:
            rejections.append(
                NormalizationRejection(
                    item_id=item_id,
                    reason_codes=["unsupported_event_type"],
                )
            )
            continue
        candidates.append(
            EventCandidate(
                item=item,
                classification=classification,
                published_at=_parse_timestamp(str(item["published_at"])),
                title_tokens=frozenset(_title_tokens(str(item["headline"]))),
            )
        )

    candidates.sort(
        key=lambda candidate: (
            candidate.published_at,
            str(candidate.item["item_id"]),
        )
    )
    groups: List[List[EventCandidate]] = []
    for candidate in candidates:
        matched_group = next(
            (
                group
                for group in groups
                if _same_event_candidate(group[0], candidate)
            ),
            None,
        )
        if matched_group is None:
            groups.append([candidate])
        else:
            matched_group.append(candidate)

    events = [
        _build_event(group, generated_at)
        for group in groups
    ]
    events.sort(
        key=lambda event: (
            event.source_refs[0].published_at or "",
            event.event_id,
        ),
        reverse=True,
    )
    return events, rejections


def classify_headline(headline: str) -> Optional[HeadlineClassification]:
    normalized = " ".join(headline.casefold().split())
    if not normalized:
        return None
    entities = ["federal_reserve_board"]

    monetary_terms = (
        "fomc",
        "federal open market committee",
        "monetary policy",
        "discount rate",
        "interest rate",
    )
    if any(term in normalized for term in monetary_terms):
        if "fomc" in normalized or "federal open market committee" in normalized:
            entities.append("federal_open_market_committee")
        if "minutes" in normalized:
            action = "publishes_meeting_minutes"
        elif "statement" in normalized:
            action = "issues_policy_statement"
        elif "projection" in normalized:
            action = "publishes_economic_projections"
        else:
            action = "publishes_monetary_policy_announcement"
        return HeadlineClassification(
            event_type="central_bank",
            normalized_action=action,
            topics=("monetary_policy",),
            entity_ids=tuple(entities),
            mapping_rule_id="federal_reserve_monetary_headline_v1",
            extraction_quality_score=0.95,
            mapping_quality_score=0.95,
        )

    regulatory_terms = (
        "enforcement action",
        "requests comment",
        "request for comment",
        "proposal",
        "final rule",
        "application",
        "stress test",
        "supervisory",
        "regulatory",
    )
    if any(term in normalized for term in regulatory_terms):
        if "enforcement action" in normalized:
            action = "issues_enforcement_action"
        elif "requests comment" in normalized or "request for comment" in normalized:
            action = "requests_regulatory_comment"
        elif "application" in normalized and (
            "approval" in normalized or "approves" in normalized
        ):
            action = "approves_application"
        elif "stress test" in normalized:
            action = "publishes_stress_test_update"
        else:
            action = "publishes_regulatory_action"
        topics = ["regulation"]
        if any(term in normalized for term in ("stablecoin", "crypto", "digital asset")):
            topics.append("crypto_market_structure")
        return HeadlineClassification(
            event_type="regulatory",
            normalized_action=action,
            topics=tuple(topics),
            entity_ids=tuple(entities),
            mapping_rule_id="federal_reserve_regulatory_headline_v1",
            extraction_quality_score=0.90,
            mapping_quality_score=0.90,
        )

    macro_terms = (
        "economic projections",
        "economic projection",
        "payments study",
        "survey",
        "industrial production",
        "consumer credit",
        "financial accounts",
    )
    if any(term in normalized for term in macro_terms):
        topics: List[str] = []
        if any(term in normalized for term in ("price", "inflation")):
            topics.append("inflation")
        if any(term in normalized for term in ("employment", "labor")):
            topics.append("labor_market")
        return HeadlineClassification(
            event_type="macro_release",
            normalized_action="publishes_macro_release",
            topics=tuple(topics),
            entity_ids=tuple(entities),
            mapping_rule_id="federal_reserve_macro_headline_v1",
            extraction_quality_score=0.85,
            mapping_quality_score=0.85,
        )
    return None


def _same_event_candidate(
    primary: EventCandidate,
    candidate: EventCandidate,
) -> bool:
    if primary.classification.event_type != candidate.classification.event_type:
        return False
    if (
        primary.classification.normalized_action
        != candidate.classification.normalized_action
    ):
        return False
    if not set(primary.classification.entity_ids).intersection(
        candidate.classification.entity_ids
    ):
        return False
    hours = abs((candidate.published_at - primary.published_at).total_seconds()) / 3600
    if hours > DEDUPE_WINDOW_HOURS:
        return False
    return _jaccard(primary.title_tokens, candidate.title_tokens) >= DEDUPE_THRESHOLD


def _build_event(
    group: Sequence[EventCandidate],
    generated_at: str,
) -> NormalizedNewsEvent:
    primary = min(
        group,
        key=lambda candidate: (
            int(candidate.item["quality_tier"]),
            candidate.published_at,
            str(candidate.item["item_id"]),
        ),
    )
    classification = primary.classification
    item_ids = sorted(str(candidate.item["item_id"]) for candidate in group)
    sources = [_source_reference(candidate.item) for candidate in group]
    sources.sort(
        key=lambda source: (
            source.quality_tier,
            source.published_at or "",
            source.source_id,
        )
    )
    similarities = [
        _jaccard(primary.title_tokens, candidate.title_tokens)
        for candidate in group
    ]
    deduplication_score = min(similarities) if similarities else 1.0
    canonical_hash = _canonical_hash(primary)
    event_id = _event_id(canonical_hash)
    mapping_rules = [*BASE_MAPPING_RULES, classification.mapping_rule_id]
    return NormalizedNewsEvent(
        event_id=event_id,
        event_type=classification.event_type,
        status="success",
        title=str(primary.item["headline"]),
        summary=None,
        occurred_at=None,
        scheduled_at=None,
        country_codes=["US"],
        entity_ids=list(classification.entity_ids),
        candidate_assets=[],
        topics=list(classification.topics),
        source_refs=sources,
        canonical_hash=canonical_hash,
        duplicate_of=None,
        normalization=EventNormalization(
            input_item_ids=item_ids,
            method="headline_rules",
            rule_version=RULE_VERSION,
            normalized_action=classification.normalized_action,
            event_key_fields=list(EVENT_KEY_FIELDS),
            mapping_rule_ids=mapping_rules,
            extraction_quality_score=classification.extraction_quality_score,
            mapping_quality_score=classification.mapping_quality_score,
            verification_level="official",
            deduplication_rule_id=(
                DEDUPE_RULE_ID if len(group) > 1 else "single_item_v1"
            ),
            deduplication_score=round(deduplication_score, 6),
        ),
        event_version=1,
        lifecycle_status="confirmed",
        lifecycle_updated_at=generated_at,
        lifecycle_reason_code="tier1_official_source_v1",
        retraction_source_ids=[],
    )


def _source_reference(item: Dict[str, Any]) -> SourceReference:
    return SourceReference(
        source_id=_source_id(str(item["item_id"])),
        provider=str(item["provider"]),
        publisher=str(item["publisher"]),
        source_type=str(item["source_type"]),
        quality_tier=int(item["quality_tier"]),
        title=str(item["headline"]),
        url=str(item["canonical_url"]),
        published_at=str(item["published_at"]),
        retrieved_at=str(item["retrieved_at"]),
        content_hash=str(item["content_hash"]),
    )


def _event_id(canonical_hash: str) -> str:
    return f"evt_news_{canonical_hash.removeprefix('sha256:')[:16]}"


def _source_id(item_id: str) -> str:
    digest = hashlib.sha256(item_id.encode("utf-8")).hexdigest()
    return f"src_news_{digest[:16]}"


def _canonical_hash(candidate: EventCandidate) -> str:
    bucket = int(candidate.published_at.timestamp()) // 7200
    key = {
        "event_type": candidate.classification.event_type,
        "entity_ids": sorted(candidate.classification.entity_ids),
        "normalized_action": candidate.classification.normalized_action,
        "title_tokens": sorted(candidate.title_tokens),
        "publication_bucket_2h": bucket,
    }
    digest = hashlib.sha256(
        json.dumps(key, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return f"sha256:{digest}"


def _title_tokens(value: str) -> List[str]:
    tokens = re.findall(r"[a-z0-9]+", value.casefold())
    return [token for token in tokens if token not in STOP_WORDS]


def _jaccard(left: frozenset[str], right: frozenset[str]) -> float:
    if not left and not right:
        return 1.0
    union = left.union(right)
    return len(left.intersection(right)) / len(union) if union else 0.0


def _parse_timestamp(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timestamp must include timezone")
    return parsed.astimezone(timezone.utc)


def _iso_utc(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
