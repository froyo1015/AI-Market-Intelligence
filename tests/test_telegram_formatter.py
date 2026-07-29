from src.telegram.formatter import (
    TELEGRAM_MESSAGE_LIMIT,
    format_telegram_messages,
)


def test_formatter_converts_headings_and_preserves_grounding_metadata() -> None:
    markdown = """# 今日市場焦點

## 美股

- SPY：價格 123.45
- [來源: test_source; timestamp: 2026-07-29T04:00:00Z]

## 今日風險

- 波動風險未知
"""

    messages = format_telegram_messages(markdown)

    assert len(messages) == 1
    assert messages[0].startswith("📊 今日市場焦點")
    assert "🇺🇸 美股" in messages[0]
    assert "• SPY：價格 123.45" in messages[0]
    assert "[來源: test_source; timestamp: 2026-07-29T04:00:00Z]" in messages[0]
    assert "⚠️ 今日風險" in messages[0]


def test_formatter_splits_long_output_within_telegram_limit() -> None:
    markdown = "# 今日市場焦點\n\n" + ("市場資料 " * 1500)

    messages = format_telegram_messages(markdown)

    assert len(messages) > 1
    assert all(0 < len(message) <= TELEGRAM_MESSAGE_LIMIT for message in messages)


def test_formatter_rejects_empty_brief() -> None:
    try:
        format_telegram_messages(" \n ")
    except ValueError as exc:
        assert "empty" in str(exc)
    else:
        raise AssertionError("expected an empty brief to be rejected")

