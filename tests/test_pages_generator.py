from src.pages.generator import generate_page


def _markdown() -> str:
    return """# 今日市場焦點

📌 測試市場摘要。[來源: context_source; timestamp: 2026-07-29T10:00:00Z]

## 美股

- SPY：價格 123.45。[來源: market_source; timestamp: 2026-07-29T04:00:00Z]

## Crypto

- BTC-USD：資料未知。[來源: market_source; timestamp: 2026-07-29T00:00:00Z]

## 黃金

- GOLD：價格 4567.89。[來源: market_source; timestamp: 2026-07-29T04:00:00Z]

## 外匯

- EURUSD：價格 1.123456。[來源: market_source; timestamp: 2026-07-29T00:00:00Z]

## 今日風險

- 免費資料可能延遲。
"""


def _snapshot() -> dict:
    return {
        "generated_at": "2026-07-29T12:00:00Z",
        "source": "market_source",
        "records": [],
    }


def test_page_contains_required_content_and_metadata() -> None:
    page = generate_page(_markdown(), _snapshot())

    assert "<!doctype html>" in page
    assert 'lang="zh-Hant"' in page
    assert "2026-07-29" in page
    for section_id in ("equities", "crypto", "gold", "forex", "risk"):
        assert f'id="{section_id}"' in page
    for label in ("今日市場焦點", "美股", "Crypto", "黃金", "外匯", "今日風險"):
        assert label in page
    assert "生成時間" in page
    assert "資料來源" in page
    assert "資料時間範圍" in page
    assert "資料新鮮度" in page
    assert "🟢 0 current" in page
    assert "market_source" in page
    assert "2026-07-29T12:00:00Z" in page


def test_page_escapes_untrusted_markdown_html() -> None:
    malicious = _markdown().replace(
        "測試市場摘要",
        '<script>alert("x")</script>',
    )

    page = generate_page(malicious, _snapshot())

    assert "<script>" not in page
    assert "&lt;script&gt;" in page
    assert "default-src &#x27;none&#x27;" not in page
    assert "default-src 'none'" in page
