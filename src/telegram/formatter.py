"""Format the generated Markdown brief for Telegram's text-message limits."""

from __future__ import annotations

from typing import Dict, List


TELEGRAM_MESSAGE_LIMIT = 4096
DEFAULT_CHUNK_SIZE = 3900

HEADING_LABELS: Dict[str, str] = {
    "# 今日市場焦點": "📊 今日市場焦點",
    "## 美股": "🇺🇸 美股",
    "## Crypto": "₿ Crypto",
    "## 黃金": "🟡 黃金",
    "## 外匯": "💱 外匯",
    "## 今日風險": "⚠️ 今日風險",
}


def format_telegram_messages(
    markdown: str,
    max_length: int = DEFAULT_CHUNK_SIZE,
) -> List[str]:
    """Convert a Markdown brief to plain Telegram text and split it safely."""
    if not isinstance(markdown, str) or not markdown.strip():
        raise ValueError("market brief is empty")
    if max_length < 1 or max_length > TELEGRAM_MESSAGE_LIMIT:
        raise ValueError(
            f"max_length must be between 1 and {TELEGRAM_MESSAGE_LIMIT}"
        )

    formatted_lines = [_format_line(line) for line in markdown.strip().splitlines()]
    formatted = "\n".join(formatted_lines).strip()
    return _split_text(formatted, max_length)


def _format_line(line: str) -> str:
    stripped = line.strip()
    if stripped in HEADING_LABELS:
        return HEADING_LABELS[stripped]
    if stripped.startswith("- "):
        indentation = line[: len(line) - len(line.lstrip())]
        return f"{indentation}• {stripped[2:]}"
    if stripped.startswith("#"):
        return stripped.lstrip("#").strip()
    return line.rstrip()


def _split_text(text: str, max_length: int) -> List[str]:
    chunks: List[str] = []
    current = ""

    for original_line in text.splitlines():
        line = original_line
        candidate = line if not current else f"{current}\n{line}"
        if len(candidate) <= max_length:
            current = candidate
            continue

        if current:
            chunks.append(current.rstrip())
            current = ""

        while len(line) > max_length:
            chunks.append(line[:max_length])
            line = line[max_length:]
        current = line

    if current:
        chunks.append(current.rstrip())

    return [chunk for chunk in chunks if chunk]

