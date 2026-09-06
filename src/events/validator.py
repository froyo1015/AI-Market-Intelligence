"""Contract validation for Phase 6.2-C2 news normalization artifacts."""

from __future__ import annotations

import hashlib
import re
from datetime import date, datetime
from typing import Any, Mapping, Sequence, Set
from urllib.parse import urlsplit

from src.data.freshness import validate_freshness_contract
from src.events.normalizer import (
    BASE_MAPPING_RULES,
    DEDUPE_RULE_ID,
    EVENT_KEY_FIELDS,
    RULE_VERSION,
)


HASH_PATTERN = re.compile(r"sha256:[0-9a-f]{64}")
EVENT_ID_PATTERN = re.compile(r"evt_news_[0-9a-f]{16}")
SOURCE_ID_PATTERN = re.compile(r"src_news_[0-9a-f]{16}")
CAUSAL_LANGUAGE = re.compile(
    r"\b(?:because|caused|causes|due to|led to|driven by)\b|"
    r"因為|由於|導致|造成|驅動",
    re.IGNORECASE,
)
PROHIBITED_KEYS = {
    "asset_impact",
    "bullish",
    "llm",
    "market_impact",
    "negative_sentiment",
    "prediction",
    "price_impact",
    "rank",
    "ranking",
    "recommendation",
    "sentiment",
}
VALID_EVENT_TYPES = {
    "macro_release",
    "central_bank",
    "company",
    "crypto",
    "geopolitical",
    "commodity",
    "regulatory",
}
VALID_TOPICS = {
    "monetary_policy",
    "inflation",
    "labor_market",
    "earnings",
    "corporate_guidance",
    "regulation",
    "crypto_market_structure",
    "energy_supply",
    "geopolitical_risk",
}
ALLOWED_ENTITIES = {
    "federal_reserve_board",
    "federal_open_market_committee",
}
EVENT_RULES = {
    "central_bank": {
        "mapping_rule": "federal_reserve_monetary_headline_v1",
        "actions": {
            "publishes_meeting_minutes",
            "issues_policy_statement",
            "publishes_economic_projections",
            "publishes_monetary_policy_announcement",
        },
        "required_topics": {"monetary_policy"},
        "allowed_topics": {"monetary_policy"},
    },
    "regulatory": {
        "mapping_rule": "federal_reserve_regulatory_headline_v1",
        "actions": {
            "issues_enforcement_action",
            "requests_regulatory_comment",
            "approves_application",
            "publishes_stress_test_update",
            "publishes_regulatory_action",
        },
        "required_topics": {"regulation"},
        "allowed_topics": {"regulation", "crypto_market_structure"},
    },
    "macro_release": {
        "mapping_rule": "federal_reserve_macro_headline_v1",
        "actions": {"publishes_macro_release"},
        "required_topics": set(),
        "allowed_topics": {"inflation", "labor_market"},
    },
}
APPROVED_SOURCE_URL = "https://www.federalreserve.gov/feeds/press_all.xml"
APPROVED_ITEM_HOSTS = {"federalreserve.gov", "www.federalreserve.gov"}


class NewsNormalizationValidationError(ValueError):
    """Raised when a C2 input or output violates the frozen contract."""


def validate_news_items_artifact(artifact: Mapping[str, Any]) -> None:
    """Validate the accepted-item boundary consumed by C2."""
    if "freshness_contract_version" in artifact:
        validate_freshness_contract(artifact)
    _validate_envelope(artifact, "news_items", {"1.0"})
    if artifact.get("status") not in {"complete", "partial", "failed"}:
        raise NewsNormalizationValidationError("news_items.status is invalid")
    if not isinstance(artifact.get("retryable"), bool):
        raise NewsNormalizationValidationError("news_items.retryable must be boolean")
    _required_string(artifact, "source", "news_items")
    if artifact.get("source") != "federal_reserve_press_releases":
        raise NewsNormalizationValidationError(
            "news_items.source is not approved for the C2 runtime"
        )
    _validate_https(_required_string(artifact, "source_url", "news_items"), "source_url")
    if artifact.get("source_url") != APPROVED_SOURCE_URL:
        raise NewsNormalizationValidationError(
            "news_items.source_url is not approved for the C2 runtime"
        )
    _validate_timestamp(
        _required_string(artifact, "window_start", "news_items"),
        "news_items.window_start",
    )
    _validate_timestamp(
        _required_string(artifact, "window_end", "news_items"),
        "news_items.window_end",
    )
    items = artifact.get("items")
    rejections = artifact.get("rejections")
    if not isinstance(items, list) or not isinstance(rejections, list):
        raise NewsNormalizationValidationError(
            "news_items items and rejections must be lists"
        )
    if artifact.get("accepted_count") != len(items):
        raise NewsNormalizationValidationError("news_items accepted_count mismatch")
    if artifact.get("rejected_count") != len(rejections):
        raise NewsNormalizationValidationError("news_items rejected_count mismatch")
    if artifact.get("status") == "failed" and items:
        raise NewsNormalizationValidationError("failed news artifact contains items")

    item_ids: Set[str] = set()
    for item in items:
        if not isinstance(item, dict):
            raise NewsNormalizationValidationError("NewsItem must be an object")
        item_id = _required_string(item, "item_id", "NewsItem")
        if item_id in item_ids:
            raise NewsNormalizationValidationError(f"duplicate item_id: {item_id}")
        item_ids.add(item_id)
        for field in ("headline", "publisher", "provider", "language"):
            _required_string(item, field, item_id)
        if item.get("source_type") not in {
            "official",
            "original_publisher",
            "aggregator",
        }:
            raise NewsNormalizationValidationError(
                f"{item_id}.source_type is invalid"
            )
        if item.get("quality_tier") not in {1, 2, 3}:
            raise NewsNormalizationValidationError(
                f"{item_id}.quality_tier is invalid"
            )
        if (
            item.get("provider") != "federal_reserve_press_releases"
            or item.get("source_type") != "official"
            or item.get("quality_tier") != 1
        ):
            raise NewsNormalizationValidationError(
                f"{item_id} is outside the approved C2 source policy"
            )
        _validate_https(
            _required_string(item, "source_url", item_id),
            f"{item_id}.source_url",
        )
        canonical_url = _required_string(item, "canonical_url", item_id)
        _validate_https(
            canonical_url,
            f"{item_id}.canonical_url",
        )
        if (urlsplit(canonical_url).hostname or "").casefold() not in APPROVED_ITEM_HOSTS:
            raise NewsNormalizationValidationError(
                f"{item_id}.canonical_url has an unapproved host"
            )
        for field in ("published_at", "retrieved_at"):
            _validate_timestamp(
                _required_string(item, field, item_id),
                f"{item_id}.{field}",
            )
        content_hash = _required_string(item, "content_hash", item_id)
        if not HASH_PATTERN.fullmatch(content_hash):
            raise NewsNormalizationValidationError(
                f"{item_id}.content_hash must be a SHA-256 digest"
            )


def validate_events_artifact(
    artifact: Mapping[str, Any],
    news_artifact: Mapping[str, Any],
) -> None:
    """Validate provenance and enforce the no-intelligence C2 boundary."""
    if "freshness_contract_version" in artifact:
        validate_freshness_contract(artifact)
    validate_news_items_artifact(news_artifact)
    _validate_envelope(artifact, "events", {"1.1"})
    _reject_prohibited_keys(artifact)
    if artifact.get("run_id") != news_artifact.get("run_id"):
        raise NewsNormalizationValidationError("events and news_items run_id mismatch")
    if artifact.get("report_date") != news_artifact.get("report_date"):
        raise NewsNormalizationValidationError(
            "events and news_items report_date mismatch"
        )
    if artifact.get("input_artifact") != "news_items.json":
        raise NewsNormalizationValidationError("events.input_artifact is invalid")
    if artifact.get("input_run_id") != news_artifact.get("run_id"):
        raise NewsNormalizationValidationError("events.input_run_id mismatch")
    if artifact.get("status") not in {"complete", "partial", "failed"}:
        raise NewsNormalizationValidationError("events.status is invalid")

    events = artifact.get("events")
    rejections = artifact.get("normalization_rejections")
    if not isinstance(events, list) or not isinstance(rejections, list):
        raise NewsNormalizationValidationError(
            "events and normalization_rejections must be lists"
        )
    if artifact.get("event_count") != len(events):
        raise NewsNormalizationValidationError("events.event_count mismatch")
    if artifact.get("normalization_rejection_count") != len(rejections):
        raise NewsNormalizationValidationError(
            "events.normalization_rejection_count mismatch"
        )
    if news_artifact.get("status") == "failed":
        expected_status = "failed"
    elif news_artifact["items"] and not events:
        expected_status = "failed"
    elif news_artifact.get("status") == "partial" or rejections:
        expected_status = "partial"
    else:
        expected_status = "complete"
    if artifact.get("status") != expected_status:
        raise NewsNormalizationValidationError(
            f"events.status must be {expected_status} for its input and counts"
        )

    inputs = {item["item_id"]: item for item in news_artifact["items"]}
    rejected_ids: Set[str] = set()
    for rejection in rejections:
        if not isinstance(rejection, dict):
            raise NewsNormalizationValidationError(
                "normalization rejection must be an object"
            )
        item_id = _required_string(rejection, "item_id", "rejection")
        if item_id not in inputs or item_id in rejected_ids:
            raise NewsNormalizationValidationError(
                f"normalization rejection has invalid item_id: {item_id}"
            )
        rejected_ids.add(item_id)
        _string_list(rejection.get("reason_codes"), "reason_codes", item_id, nonempty=True)

    event_ids: Set[str] = set()
    consumed_ids: Set[str] = set()
    for event in events:
        if not isinstance(event, dict):
            raise NewsNormalizationValidationError("event must be an object")
        event_id = _required_string(event, "event_id", "event")
        if not EVENT_ID_PATTERN.fullmatch(event_id) or event_id in event_ids:
            raise NewsNormalizationValidationError(f"invalid or duplicate event_id: {event_id}")
        event_ids.add(event_id)
        _validate_event(event, inputs, consumed_ids)

    if consumed_ids.intersection(rejected_ids):
        raise NewsNormalizationValidationError(
            "a NewsItem cannot be both normalized and rejected"
        )
    if consumed_ids.union(rejected_ids) != set(inputs):
        raise NewsNormalizationValidationError(
            "every accepted NewsItem must be normalized or rejected"
        )


def _validate_event(
    event: Mapping[str, Any],
    inputs: Mapping[str, Mapping[str, Any]],
    consumed_ids: Set[str],
) -> None:
    event_id = str(event["event_id"])
    if event.get("event_type") not in VALID_EVENT_TYPES:
        raise NewsNormalizationValidationError(f"{event_id}.event_type is invalid")
    if event.get("status") != "success":
        raise NewsNormalizationValidationError(f"{event_id}.status must be success")
    title = _required_string(event, "title", event_id)
    if CAUSAL_LANGUAGE.search(title):
        raise NewsNormalizationValidationError(f"{event_id}.title is causal")
    if event.get("summary") is not None:
        raise NewsNormalizationValidationError(f"{event_id}.summary must be null in C2")
    if event.get("occurred_at") is not None or event.get("scheduled_at") is not None:
        raise NewsNormalizationValidationError(
            f"{event_id} cannot infer event time from publication time"
        )
    if _string_list(event.get("country_codes"), "country_codes", event_id) != ["US"]:
        raise NewsNormalizationValidationError(f"{event_id}.country_codes is invalid")
    entity_ids = _string_list(
        event.get("entity_ids"), "entity_ids", event_id, nonempty=True
    )
    if (
        "federal_reserve_board" not in entity_ids
        or any(entity not in ALLOWED_ENTITIES for entity in entity_ids)
    ):
        raise NewsNormalizationValidationError(f"{event_id}.entity_ids is invalid")
    if _string_list(event.get("candidate_assets"), "candidate_assets", event_id):
        raise NewsNormalizationValidationError(
            f"{event_id}.candidate_assets must remain empty in C2"
        )
    topics = _string_list(event.get("topics"), "topics", event_id)
    if any(topic not in VALID_TOPICS for topic in topics):
        raise NewsNormalizationValidationError(f"{event_id}.topics is invalid")
    runtime_rule = EVENT_RULES.get(str(event.get("event_type")))
    if runtime_rule is None:
        raise NewsNormalizationValidationError(
            f"{event_id}.event_type is not supported by C2 runtime rules"
        )
    topic_set = set(topics)
    if not runtime_rule["required_topics"].issubset(topic_set) or not topic_set.issubset(
        runtime_rule["allowed_topics"]
    ):
        raise NewsNormalizationValidationError(
            f"{event_id}.topics conflict with event_type"
        )
    canonical_hash = _required_string(event, "canonical_hash", event_id)
    if not HASH_PATTERN.fullmatch(canonical_hash):
        raise NewsNormalizationValidationError(f"{event_id}.canonical_hash is invalid")
    if event_id != f"evt_news_{canonical_hash.removeprefix('sha256:')[:16]}":
        raise NewsNormalizationValidationError(
            f"{event_id} does not match its canonical event key"
        )
    if event.get("duplicate_of") is not None:
        raise NewsNormalizationValidationError(
            f"{event_id}.duplicate_of must be null after canonical merging"
        )

    normalization = event.get("normalization")
    if not isinstance(normalization, dict):
        raise NewsNormalizationValidationError(f"{event_id}.normalization is invalid")
    input_ids = _string_list(
        normalization.get("input_item_ids"),
        "normalization.input_item_ids",
        event_id,
        nonempty=True,
    )
    if len(input_ids) != len(set(input_ids)) or any(item not in inputs for item in input_ids):
        raise NewsNormalizationValidationError(f"{event_id} has invalid input_item_ids")
    if consumed_ids.intersection(input_ids):
        raise NewsNormalizationValidationError("a NewsItem appears in multiple events")
    consumed_ids.update(input_ids)
    if title not in {str(inputs[item]["headline"]) for item in input_ids}:
        raise NewsNormalizationValidationError(f"{event_id}.title introduces unsupported facts")
    if normalization.get("method") != "headline_rules":
        raise NewsNormalizationValidationError(f"{event_id}.method is invalid")
    if normalization.get("rule_version") != RULE_VERSION:
        raise NewsNormalizationValidationError(f"{event_id}.rule_version is invalid")
    if normalization.get("event_key_fields") != EVENT_KEY_FIELDS:
        raise NewsNormalizationValidationError(f"{event_id}.event_key_fields is invalid")
    if normalization.get("normalized_action") not in runtime_rule["actions"]:
        raise NewsNormalizationValidationError(
            f"{event_id}.normalized_action conflicts with event_type"
        )
    mapping_rules = _string_list(
        normalization.get("mapping_rule_ids"),
        "normalization.mapping_rule_ids",
        event_id,
        nonempty=True,
    )
    expected_mapping_rules = [*BASE_MAPPING_RULES, runtime_rule["mapping_rule"]]
    if mapping_rules != expected_mapping_rules:
        raise NewsNormalizationValidationError(f"{event_id}.mapping_rule_ids is invalid")
    for field in ("extraction_quality_score", "mapping_quality_score", "deduplication_score"):
        score = normalization.get(field)
        if not _is_number(score) or not 0.0 <= float(score) <= 1.0:
            raise NewsNormalizationValidationError(f"{event_id}.{field} is invalid")
    if normalization.get("verification_level") != "official":
        raise NewsNormalizationValidationError(f"{event_id}.verification_level is invalid")
    expected_dedupe = DEDUPE_RULE_ID if len(input_ids) > 1 else "single_item_v1"
    if normalization.get("deduplication_rule_id") != expected_dedupe:
        raise NewsNormalizationValidationError(f"{event_id}.deduplication_rule_id is invalid")

    sources = event.get("source_refs")
    if not isinstance(sources, list) or len(sources) != len(input_ids):
        raise NewsNormalizationValidationError(f"{event_id}.source_refs is invalid")
    source_ids: Set[str] = set()
    for source in sources:
        if not isinstance(source, dict):
            raise NewsNormalizationValidationError("source reference must be an object")
        source_id = _required_string(source, "source_id", event_id)
        if not SOURCE_ID_PATTERN.fullmatch(source_id) or source_id in source_ids:
            raise NewsNormalizationValidationError(f"{event_id} has invalid source_id")
        source_ids.add(source_id)
        matches = [
            item
            for item_id, item in inputs.items()
            if item_id in input_ids
            and source.get("title") == item["headline"]
            and source.get("url") == item["canonical_url"]
            and source.get("content_hash") == item["content_hash"]
        ]
        if len(matches) != 1:
            raise NewsNormalizationValidationError(
                f"{event_id} source reference does not resolve to one NewsItem"
            )
        match = matches[0]
        expected_source_id = "src_news_" + hashlib.sha256(
            str(match["item_id"]).encode("utf-8")
        ).hexdigest()[:16]
        if source_id != expected_source_id:
            raise NewsNormalizationValidationError(
                f"{event_id} source_id does not match its NewsItem"
            )
        for source_field, item_field in (
            ("provider", "provider"),
            ("publisher", "publisher"),
            ("source_type", "source_type"),
            ("quality_tier", "quality_tier"),
            ("published_at", "published_at"),
            ("retrieved_at", "retrieved_at"),
        ):
            if source.get(source_field) != match[item_field]:
                raise NewsNormalizationValidationError(
                    f"{event_id} source {source_field} mismatch"
                )

    if event.get("event_version") != 1 or event.get("lifecycle_status") != "confirmed":
        raise NewsNormalizationValidationError(f"{event_id} lifecycle is invalid")
    _validate_timestamp(
        _required_string(event, "lifecycle_updated_at", event_id),
        f"{event_id}.lifecycle_updated_at",
    )
    if event.get("lifecycle_reason_code") != "tier1_official_source_v1":
        raise NewsNormalizationValidationError(f"{event_id} lifecycle reason is invalid")
    if _string_list(event.get("retraction_source_ids"), "retraction_source_ids", event_id):
        raise NewsNormalizationValidationError(f"{event_id} retraction sources are invalid")


def _validate_envelope(
    artifact: Mapping[str, Any], artifact_type: str, versions: Set[str]
) -> None:
    if artifact.get("schema_version") not in versions:
        raise NewsNormalizationValidationError(
            f"{artifact_type}.schema_version is unsupported"
        )
    if artifact.get("artifact_type") != artifact_type:
        raise NewsNormalizationValidationError(f"expected artifact_type {artifact_type}")
    _required_string(artifact, "run_id", artifact_type)
    try:
        date.fromisoformat(_required_string(artifact, "report_date", artifact_type))
    except ValueError as exc:
        raise NewsNormalizationValidationError(
            f"{artifact_type}.report_date is invalid"
        ) from exc
    _validate_timestamp(
        _required_string(artifact, "generated_at", artifact_type),
        f"{artifact_type}.generated_at",
    )
    warnings = artifact.get("warnings")
    if not isinstance(warnings, list) or any(not isinstance(item, str) for item in warnings):
        raise NewsNormalizationValidationError(f"{artifact_type}.warnings is invalid")


def _reject_prohibited_keys(value: Any) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if str(key).casefold() in PROHIBITED_KEYS:
                raise NewsNormalizationValidationError(
                    f"prohibited C2 field present: {key}"
                )
            _reject_prohibited_keys(child)
    elif isinstance(value, list):
        for child in value:
            _reject_prohibited_keys(child)


def _required_string(value: Mapping[str, Any], field: str, context: str) -> str:
    item = value.get(field)
    if not isinstance(item, str) or not item.strip():
        raise NewsNormalizationValidationError(
            f"{context}.{field} must be a non-empty string"
        )
    return item


def _string_list(
    value: Any,
    field: str,
    context: str,
    nonempty: bool = False,
) -> list[str]:
    if not isinstance(value, list) or any(
        not isinstance(item, str) or not item for item in value
    ):
        raise NewsNormalizationValidationError(f"{context}.{field} must be a string list")
    if nonempty and not value:
        raise NewsNormalizationValidationError(f"{context}.{field} cannot be empty")
    return value


def _validate_timestamp(value: str, context: str) -> None:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise NewsNormalizationValidationError(f"{context} is invalid") from exc
    if parsed.tzinfo is None:
        raise NewsNormalizationValidationError(f"{context} must include timezone")


def _validate_https(value: str, context: str) -> None:
    parsed = urlsplit(value)
    if parsed.scheme.casefold() != "https" or not parsed.hostname:
        raise NewsNormalizationValidationError(f"{context} must be an HTTPS URL")


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)
