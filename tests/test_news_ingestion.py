from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from src.data.news_adapter import (
    FEDERAL_RESERVE_PUBLISHER,
    FEDERAL_RESERVE_RSS_URL,
    NewsSourceAccessError,
    NewsSourcePayload,
)
from src.news_pipeline import build_news_items_artifact


def _feed(*items: str, language: str = "en") -> str:
    return (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<rss version="2.0"><channel>'
        '<title>FRB: Press Release - All Releases</title>'
        f"<language>{language}</language>"
        f"{''.join(items)}"
        "</channel></rss>"
    )


def _item(
    identifier: str = "https://www.federalreserve.gov/item-1",
    title: str = "Federal Reserve publishes an official announcement",
    link: str = (
        "https://www.federalreserve.gov/newsevents/pressreleases/"
        "monetary20260819a.htm"
    ),
    description: str = "<b>Official</b> source-provided description",
    published_at: str = "Wed, 19 Aug 2026 10:00:00 GMT",
) -> str:
    return (
        "<item>"
        f"<title>{title}</title>"
        f"<link><![CDATA[{link}]]></link>"
        f"<guid><![CDATA[{identifier}]]></guid>"
        f"<description><![CDATA[{description}]]></description>"
        "<category>Monetary Policy</category>"
        f"<pubDate><![CDATA[{published_at}]]></pubDate>"
        "</item>"
    )


class FakeNewsAdapter:
    source_name = "federal_reserve_press_releases"
    publisher = FEDERAL_RESERVE_PUBLISHER
    source_url = FEDERAL_RESERVE_RSS_URL
    source_type = "official"
    quality_tier = 1

    def __init__(self, content: str) -> None:
        self.content = content

    def fetch(self, now=None) -> NewsSourcePayload:
        return NewsSourcePayload(
            content=self.content,
            retrieved_at=now,
            source=self.source_name,
            publisher=self.publisher,
            source_url=self.source_url,
            source_type=self.source_type,
            quality_tier=self.quality_tier,
        )


class FailedNewsAdapter(FakeNewsAdapter):
    def __init__(self) -> None:
        super().__init__("")

    def fetch(self, now=None) -> NewsSourcePayload:
        raise NewsSourceAccessError("simulated RSS outage")


NOW = datetime(2026, 8, 19, 12, tzinfo=timezone.utc)


def test_news_ingestion_preserves_tier_one_source_contract() -> None:
    artifact = build_news_items_artifact(
        adapter=FakeNewsAdapter(_feed(_item())),
        now=NOW,
    ).to_dict()

    assert artifact["status"] == "complete"
    assert artifact["failure_type"] is None
    assert artifact["accepted_count"] == 1
    assert artifact["rejected_count"] == 0
    assert artifact["report_date"] == "2026-08-19"
    item = artifact["items"][0]
    assert item["publisher"] == FEDERAL_RESERVE_PUBLISHER
    assert item["provider"] == "federal_reserve_press_releases"
    assert item["source_type"] == "official"
    assert item["quality_tier"] == 1
    assert item["published_at"] == "2026-08-19T10:00:00Z"
    assert item["retrieved_at"] == "2026-08-19T12:00:00Z"
    assert item["source_excerpt"] == "Official source-provided description"
    assert item["content_hash"].startswith("sha256:")
    assert "event" not in item
    assert "assets" not in item


def test_window_filter_is_a_complete_empty_result_not_source_failure() -> None:
    artifact = build_news_items_artifact(
        adapter=FakeNewsAdapter(
            _feed(_item(published_at="Tue, 18 Aug 2026 05:00:00 GMT"))
        ),
        now=NOW,
    ).to_dict()

    assert artifact["status"] == "complete"
    assert artifact["failure_type"] is None
    assert artifact["retryable"] is False
    assert artifact["accepted_count"] == 0
    assert artifact["rejected_count"] == 1
    assert artifact["rejections"][0]["reason_codes"] == [
        "outside_ingestion_window"
    ]


def test_item_ids_and_hashes_ignore_retrieval_time() -> None:
    adapter = FakeNewsAdapter(_feed(_item()))
    first = build_news_items_artifact(adapter=adapter, now=NOW).to_dict()
    second = build_news_items_artifact(
        adapter=adapter,
        now=NOW + timedelta(minutes=1),
    ).to_dict()

    assert first["items"][0]["item_id"] == second["items"][0]["item_id"]
    assert first["items"][0]["content_hash"] == second["items"][0]["content_hash"]
    assert first["items"][0]["retrieved_at"] != second["items"][0]["retrieved_at"]


def test_source_correction_keeps_item_id_but_changes_content_hash() -> None:
    original = build_news_items_artifact(
        adapter=FakeNewsAdapter(_feed(_item(title="Original official title"))),
        now=NOW,
    ).to_dict()["items"][0]
    corrected = build_news_items_artifact(
        adapter=FakeNewsAdapter(_feed(_item(title="Corrected official title"))),
        now=NOW,
    ).to_dict()["items"][0]

    assert original["item_id"] == corrected["item_id"]
    assert original["content_hash"] != corrected["content_hash"]


def test_malformed_item_is_rejected_without_losing_valid_item() -> None:
    malformed = _item(title="").replace("<title></title>", "")
    artifact = build_news_items_artifact(
        adapter=FakeNewsAdapter(_feed(_item(), malformed)),
        now=NOW,
    ).to_dict()

    assert artifact["status"] == "partial"
    assert artifact["failure_type"] == "item_validation_error"
    assert artifact["accepted_count"] == 1
    assert artifact["rejected_count"] == 1
    assert artifact["rejections"][0]["reason_codes"] == ["missing_headline"]


def test_duplicate_source_item_links_to_accepted_item() -> None:
    duplicate = _item(
        identifier="https://www.federalreserve.gov/item-2",
        title="A duplicate representation of the same source item",
    )
    artifact = build_news_items_artifact(
        adapter=FakeNewsAdapter(_feed(_item(), duplicate)),
        now=NOW,
    ).to_dict()

    assert artifact["status"] == "complete"
    assert artifact["accepted_count"] == 1
    assert artifact["rejected_count"] == 1
    rejection = artifact["rejections"][0]
    assert rejection["reason_codes"] == ["duplicate_source_item"]
    assert rejection["matched_item_id"] == artifact["items"][0]["item_id"]
    assert rejection["matched_event_id"] is None


def test_source_access_failure_is_retryable_and_contains_no_fake_items() -> None:
    artifact = build_news_items_artifact(
        adapter=FailedNewsAdapter(),
        now=NOW,
    ).to_dict()

    assert artifact["status"] == "failed"
    assert artifact["failure_type"] == "source_access_error"
    assert artifact["retryable"] is True
    assert artifact["items"] == []
    assert artifact["rejections"] == []
    assert "simulated RSS outage" in artifact["warnings"][0]


def test_invalid_xml_is_non_retryable_source_validation_failure() -> None:
    artifact = build_news_items_artifact(
        adapter=FakeNewsAdapter("<rss><channel>"),
        now=NOW,
    ).to_dict()

    assert artifact["status"] == "failed"
    assert artifact["failure_type"] == "source_validation_error"
    assert artifact["retryable"] is False
    assert artifact["accepted_count"] == 0


def test_item_cap_cannot_exceed_frozen_contract() -> None:
    with pytest.raises(ValueError, match="between 1 and 100"):
        build_news_items_artifact(
            adapter=FakeNewsAdapter(_feed()),
            now=NOW,
            max_items=101,
        )
