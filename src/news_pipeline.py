"""Build the Phase 6.2-C1 source-grounded news_items.json artifact."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from src.data.news_adapter import (
    FEDERAL_RESERVE_RSS_URL,
    FederalReserveNewsAdapter,
    NewsSourceAccessError,
    NewsSourceAdapter,
    NewsSourcePayload,
    RawNewsItem,
    parse_federal_reserve_rss,
)
from src.models.news_schema import NewsItem, NewsItemsArtifact, NewsRejection


DEFAULT_OUTPUT_PATH = Path(__file__).resolve().parent / "output" / "news_items.json"
MAX_RETAINED_SOURCE_RECORDS = 100
MAX_EXCERPT_CHARACTERS = 500
DEFAULT_LOOKBACK_HOURS = 24
DEFAULT_OVERLAP_HOURS = 6
DEFAULT_FUTURE_SKEW_MINUTES = 5
ALLOWED_LANGUAGE_TAGS = {"en", "en-us"}
TRACKING_QUERY_KEYS = {"source", "ref", "campaign", "trk"}


def build_news_items_artifact(
    adapter: Optional[NewsSourceAdapter] = None,
    now: Optional[datetime] = None,
    lookback_hours: int = DEFAULT_LOOKBACK_HOURS,
    overlap_hours: int = DEFAULT_OVERLAP_HOURS,
    max_items: int = MAX_RETAINED_SOURCE_RECORDS,
    future_skew_minutes: int = DEFAULT_FUTURE_SKEW_MINUTES,
) -> NewsItemsArtifact:
    _validate_options(
        lookback_hours,
        overlap_hours,
        max_items,
        future_skew_minutes,
    )
    generated_at = _as_utc(now or datetime.now(timezone.utc))
    window_start = generated_at - timedelta(
        hours=lookback_hours + overlap_hours
    )
    window_end = generated_at + timedelta(minutes=future_skew_minutes)
    provider = adapter or FederalReserveNewsAdapter()
    source = getattr(provider, "source_name", "news_source")
    source_url = getattr(provider, "source_url", FEDERAL_RESERVE_RSS_URL)

    try:
        payload = provider.fetch(now=generated_at)
        _validate_source_payload(payload)
        language, raw_items = parse_federal_reserve_rss(payload.content)
    except NewsSourceAccessError as exc:
        return _failed_artifact(
            generated_at,
            window_start,
            window_end,
            source,
            source_url,
            "source_access_error",
            True,
            exc,
        )
    except Exception as exc:
        return _failed_artifact(
            generated_at,
            window_start,
            window_end,
            source,
            source_url,
            "source_validation_error",
            False,
            exc,
        )

    warnings: List[str] = []
    if len(raw_items) > max_items:
        warnings.append(
            f"Source returned {len(raw_items)} items; only the first "
            f"{max_items} were evaluated."
        )
    selected_items = raw_items[:max_items]
    items: List[NewsItem] = []
    rejections: List[NewsRejection] = []
    validation_error_count = 0
    accepted_by_url: Dict[str, str] = {}
    accepted_by_hash: Dict[str, str] = {}

    for raw_item in selected_items:
        item, rejection, is_validation_error = _normalize_item(
            raw_item,
            payload,
            language,
            window_start,
            window_end,
        )
        if rejection is not None:
            rejections.append(rejection)
            validation_error_count += int(is_validation_error)
            continue
        if item is None:
            raise RuntimeError("news item normalization returned no result")

        matched_item_id = accepted_by_url.get(item.canonical_url)
        if matched_item_id is None:
            matched_item_id = accepted_by_hash.get(item.content_hash)
        if matched_item_id is not None:
            rejections.append(
                NewsRejection(
                    provider_item_id=item.provider_item_id,
                    source_url=item.source_url,
                    reason_codes=["duplicate_source_item"],
                    matched_item_id=matched_item_id,
                )
            )
            continue
        items.append(item)
        accepted_by_url[item.canonical_url] = item.item_id
        accepted_by_hash[item.content_hash] = item.item_id

    items.sort(key=lambda item: (item.published_at, item.item_id), reverse=True)
    if not items:
        warnings.append(
            "No Federal Reserve press releases were published in the configured "
            "ingestion window."
        )
    if validation_error_count:
        warnings.append(
            f"{validation_error_count} source item(s) failed validation and "
            "were excluded."
        )
    return NewsItemsArtifact(
        generated_at=generated_at,
        window_start=window_start,
        window_end=window_end,
        source=payload.source,
        source_url=payload.source_url,
        status="partial" if validation_error_count else "complete",
        failure_type=("item_validation_error" if validation_error_count else None),
        retryable=False,
        warnings=warnings,
        items=items,
        rejections=rejections,
    )


def write_news_items_artifact(
    artifact: NewsItemsArtifact,
    output_path: Path = DEFAULT_OUTPUT_PATH,
) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = output_path.with_suffix(f"{output_path.suffix}.tmp")
    temporary_path.write_text(
        json.dumps(artifact.to_dict(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary_path.replace(output_path)
    return output_path


def run_news_pipeline(
    output_path: Path = DEFAULT_OUTPUT_PATH,
    lookback_hours: int = DEFAULT_LOOKBACK_HOURS,
    overlap_hours: int = DEFAULT_OVERLAP_HOURS,
    max_items: int = MAX_RETAINED_SOURCE_RECORDS,
) -> NewsItemsArtifact:
    artifact = build_news_items_artifact(
        lookback_hours=lookback_hours,
        overlap_hours=overlap_hours,
        max_items=max_items,
    )
    write_news_items_artifact(artifact, output_path)
    return artifact


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate the Phase 6.2-C1 Federal Reserve news artifact."
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    parser.add_argument("--lookback-hours", type=int, default=DEFAULT_LOOKBACK_HOURS)
    parser.add_argument("--overlap-hours", type=int, default=DEFAULT_OVERLAP_HOURS)
    parser.add_argument("--max-items", type=int, default=MAX_RETAINED_SOURCE_RECORDS)
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    artifact = run_news_pipeline(
        output_path=args.output,
        lookback_hours=args.lookback_hours,
        overlap_hours=args.overlap_hours,
        max_items=args.max_items,
    )
    payload = artifact.to_dict()
    print(
        f"Wrote {payload['accepted_count']} accepted news item(s) and "
        f"{payload['rejected_count']} rejection record(s) to {args.output}; "
        f"status={payload['status']}"
    )
    return 1 if payload["status"] == "failed" else 0


def cli() -> None:
    raise SystemExit(main())


def _normalize_item(
    raw_item: RawNewsItem,
    payload: NewsSourcePayload,
    language: str,
    window_start: datetime,
    window_end: datetime,
) -> Tuple[Optional[NewsItem], Optional[NewsRejection], bool]:
    reasons: List[str] = []
    headline = _normalize_text(raw_item.title)
    provider_item_id = _normalize_text(raw_item.provider_item_id)
    raw_url = _normalize_text(raw_item.link)
    canonical_url: Optional[str] = None
    published_at: Optional[datetime] = None

    if headline is None:
        reasons.append("missing_headline")
    try:
        canonical_url = _canonicalize_federal_reserve_url(raw_url)
    except ValueError as exc:
        reasons.append(str(exc))
    if raw_item.published_at is None:
        reasons.append("missing_published_at")
    else:
        try:
            published_at = _parse_rss_datetime(raw_item.published_at)
        except (TypeError, ValueError):
            reasons.append("invalid_published_at")
    normalized_language = language.casefold().replace("_", "-")
    if normalized_language not in ALLOWED_LANGUAGE_TAGS:
        reasons.append("unsupported_language")
    if published_at is not None:
        if published_at > window_end:
            reasons.append("published_beyond_clock_skew")
        elif published_at < window_start:
            return None, NewsRejection(
                provider_item_id=provider_item_id,
                source_url=canonical_url or raw_url,
                reason_codes=["outside_ingestion_window"],
            ), False
    if reasons:
        return None, NewsRejection(
            provider_item_id=provider_item_id,
            source_url=canonical_url or raw_url,
            reason_codes=sorted(set(reasons)),
        ), True
    if canonical_url is None or headline is None or published_at is None:
        raise RuntimeError("validated news item has incomplete required fields")

    source_excerpt = _source_excerpt(raw_item.description)
    hash_payload = {
        "headline": headline,
        "source_excerpt": source_excerpt,
        "publisher": payload.publisher,
        "provider": payload.source,
        "source_type": payload.source_type,
        "quality_tier": payload.quality_tier,
        "canonical_url": canonical_url,
        "published_at": _iso_utc(published_at),
        "language": normalized_language,
    }
    digest = hashlib.sha256(
        json.dumps(
            hash_payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    identity_material = provider_item_id or canonical_url
    identity_digest = hashlib.sha256(
        f"{payload.source}|{identity_material}".encode("utf-8")
    ).hexdigest()
    item_id = f"nws_federal_reserve_{identity_digest[:16]}"
    return NewsItem(
        item_id=item_id,
        provider_item_id=provider_item_id,
        headline=headline,
        source_excerpt=source_excerpt,
        publisher=payload.publisher,
        provider=payload.source,
        source_type=payload.source_type,
        quality_tier=payload.quality_tier,
        source_url=raw_url or canonical_url,
        canonical_url=canonical_url,
        published_at=published_at,
        retrieved_at=payload.retrieved_at,
        language=normalized_language,
        content_hash=f"sha256:{digest}",
    ), None, False


def _failed_artifact(
    generated_at: datetime,
    window_start: datetime,
    window_end: datetime,
    source: str,
    source_url: str,
    failure_type: str,
    retryable: bool,
    exc: Exception,
) -> NewsItemsArtifact:
    return NewsItemsArtifact(
        generated_at=generated_at,
        window_start=window_start,
        window_end=window_end,
        source=source,
        source_url=source_url,
        status="failed",
        failure_type=failure_type,
        retryable=retryable,
        warnings=[f"News source unavailable: {_safe_error(exc)}"],
        items=[],
        rejections=[],
    )


def _canonicalize_federal_reserve_url(value: Optional[str]) -> str:
    if value is None:
        raise ValueError("missing_canonical_url")
    parsed = urlsplit(value)
    if parsed.scheme.casefold() != "https":
        raise ValueError("invalid_canonical_url_scheme")
    hostname = (parsed.hostname or "").casefold()
    if hostname not in {"federalreserve.gov", "www.federalreserve.gov"}:
        raise ValueError("unapproved_canonical_url_host")
    try:
        port = parsed.port
    except ValueError as exc:
        raise ValueError("invalid_canonical_url_port") from exc
    if parsed.username is not None or parsed.password is not None:
        raise ValueError("invalid_canonical_url_credentials")
    if port not in {None, 443}:
        raise ValueError("invalid_canonical_url_port")
    if not re.fullmatch(
        r"/newsevents/pressreleases/[A-Za-z0-9_-]+\.htm",
        parsed.path,
    ):
        raise ValueError("unapproved_canonical_url_path")
    query = [
        (key, value)
        for key, value in parse_qsl(parsed.query, keep_blank_values=True)
        if not key.casefold().startswith("utm_")
        and key.casefold() not in TRACKING_QUERY_KEYS
    ]
    return urlunsplit(("https", "www.federalreserve.gov", parsed.path, urlencode(query), ""))


def _validate_source_payload(payload: NewsSourcePayload) -> None:
    if not payload.source.strip() or not payload.publisher.strip():
        raise ValueError("news source metadata is incomplete")
    if payload.source_type not in {"official", "original_publisher", "aggregator"}:
        raise ValueError("news source_type is unsupported")
    if payload.quality_tier not in {1, 2, 3}:
        raise ValueError("news quality_tier is unsupported")
    source_url = urlsplit(payload.source_url)
    if source_url.scheme.casefold() != "https" or not source_url.hostname:
        raise ValueError("news source_url must be an absolute HTTPS URL")
    if payload.retrieved_at.tzinfo is None:
        raise ValueError("news retrieved_at must include timezone")


def _parse_rss_datetime(value: str) -> datetime:
    parsed = parsedate_to_datetime(value)
    if parsed is None:
        raise ValueError("RSS timestamp could not be parsed")
    return _as_utc(parsed)


def _source_excerpt(value: Optional[str]) -> Optional[str]:
    normalized = _normalize_text(value)
    if normalized is None:
        return None
    parser = _PlainTextExtractor()
    parser.feed(normalized)
    parser.close()
    plain_text = _normalize_text(" ".join(parser.parts))
    return plain_text[:MAX_EXCERPT_CHARACTERS] if plain_text else None


class _PlainTextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: List[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)


def _normalize_text(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    normalized = re.sub(r"\s+", " ", value).strip()
    return normalized or None


def _validate_options(
    lookback_hours: int,
    overlap_hours: int,
    max_items: int,
    future_skew_minutes: int,
) -> None:
    if lookback_hours <= 0 or lookback_hours > 168:
        raise ValueError("lookback_hours must be between 1 and 168")
    if overlap_hours < 0 or overlap_hours > 24:
        raise ValueError("overlap_hours must be between 0 and 24")
    if max_items <= 0 or max_items > MAX_RETAINED_SOURCE_RECORDS:
        raise ValueError("max_items must be between 1 and 100")
    if future_skew_minutes < 0 or future_skew_minutes > 15:
        raise ValueError("future_skew_minutes must be between 0 and 15")


def _safe_error(exc: Exception) -> str:
    return f"{type(exc).__name__}: {' '.join(str(exc).split())}"[:300]


def _iso_utc(value: datetime) -> str:
    return _as_utc(value).isoformat().replace("+00:00", "Z")


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


if __name__ == "__main__":
    cli()
