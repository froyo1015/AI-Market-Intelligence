from pathlib import Path
from typing import Any, List, Mapping

import pytest

from src.telegram.bot import (
    TelegramBotClient,
    TelegramConfig,
    TelegramError,
    TelegramRetryableError,
    main,
    send_brief,
)


class FakeTransport:
    def __init__(self, outcomes: List[Any]) -> None:
        self.outcomes = outcomes
        self.calls: List[str] = []

    def send_message(
        self,
        config: TelegramConfig,
        text: str,
        timeout: float,
    ) -> Mapping[str, Any]:
        self.calls.append(text)
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


def _config() -> TelegramConfig:
    return TelegramConfig(token="test-token", chat_id="test-chat")


def test_send_brief_reads_formats_and_sends_file(tmp_path: Path) -> None:
    brief_path = tmp_path / "ai_market_brief.md"
    brief_path.write_text(
        "# 今日市場焦點\n\n## 美股\n\n- SPY：價格 123.45\n",
        encoding="utf-8",
    )
    transport = FakeTransport([{"ok": True, "result": {"message_id": 1}}])
    client = TelegramBotClient(_config(), transport=transport)

    message_count = send_brief(brief_path, client)

    assert message_count == 1
    assert transport.calls == ["📊 今日市場焦點\n\n🇺🇸 美股\n\n• SPY：價格 123.45"]


def test_client_retries_transient_failure_and_honors_retry_after() -> None:
    transport = FakeTransport(
        [
            TelegramRetryableError("rate limited", retry_after=2.5),
            {"ok": True, "result": {"message_id": 1}},
        ]
    )
    sleeps: List[float] = []
    client = TelegramBotClient(
        _config(),
        transport=transport,
        max_attempts=3,
        sleep=sleeps.append,
    )

    response = client.send("brief")

    assert response["ok"] is True
    assert transport.calls == ["brief", "brief"]
    assert sleeps == [2.5]


def test_client_stops_after_bounded_retries() -> None:
    transport = FakeTransport(
        [
            TelegramRetryableError("temporary"),
            TelegramRetryableError("temporary"),
            TelegramRetryableError("temporary"),
        ]
    )
    client = TelegramBotClient(
        _config(),
        transport=transport,
        max_attempts=3,
        sleep=lambda _: None,
    )

    with pytest.raises(TelegramError, match="after 3 attempts"):
        client.send("brief")

    assert len(transport.calls) == 3


def test_cli_can_skip_when_secrets_are_not_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)

    assert main(["--skip-if-unconfigured"]) == 0

