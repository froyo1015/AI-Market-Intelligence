"""Send the generated AI Market Brief through the Telegram Bot API."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Optional, Protocol, Sequence
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from src.telegram.formatter import format_telegram_messages


OUTPUT_DIRECTORY = Path(__file__).resolve().parents[1] / "output"
DEFAULT_BRIEF_PATH = OUTPUT_DIRECTORY / "ai_market_brief.md"
DEFAULT_MAX_ATTEMPTS = 3
DEFAULT_TIMEOUT_SECONDS = 15.0


class TelegramError(RuntimeError):
    """Base error for Telegram configuration and delivery failures."""


class TelegramRetryableError(TelegramError):
    """A transient failure that may succeed on a later attempt."""

    def __init__(self, message: str, retry_after: Optional[float] = None) -> None:
        super().__init__(message)
        self.retry_after = retry_after


@dataclass(frozen=True)
class TelegramConfig:
    token: str
    chat_id: str

    @classmethod
    def from_environment(cls) -> "TelegramConfig":
        token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
        chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
        missing = [
            name
            for name, value in (
                ("TELEGRAM_BOT_TOKEN", token),
                ("TELEGRAM_CHAT_ID", chat_id),
            )
            if not value
        ]
        if missing:
            raise TelegramError(
                f"missing required environment variable(s): {', '.join(missing)}"
            )
        return cls(token=token, chat_id=chat_id)


class TelegramTransport(Protocol):
    def send_message(
        self,
        config: TelegramConfig,
        text: str,
        timeout: float,
    ) -> Mapping[str, Any]:
        """Send one Telegram message and return the decoded API response."""


class UrllibTelegramTransport:
    """Small standard-library transport for Telegram's HTTPS API."""

    def send_message(
        self,
        config: TelegramConfig,
        text: str,
        timeout: float,
    ) -> Mapping[str, Any]:
        endpoint = f"https://api.telegram.org/bot{config.token}/sendMessage"
        body = json.dumps(
            {
                "chat_id": config.chat_id,
                "text": text,
                "disable_web_page_preview": True,
            }
        ).encode("utf-8")
        request = Request(
            endpoint,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urlopen(request, timeout=timeout) as response:
                payload = _decode_response(response.read())
        except HTTPError as exc:
            payload = _decode_response(exc.read(), allow_invalid=True)
            _raise_api_error(payload, fallback_code=exc.code)
        except URLError as exc:
            raise TelegramRetryableError(
                "Telegram network request failed"
            ) from exc
        except TimeoutError as exc:
            raise TelegramRetryableError("Telegram request timed out") from exc

        if payload.get("ok") is not True:
            _raise_api_error(payload)
        return payload


class TelegramBotClient:
    """Telegram sender with bounded retries and flood-control handling."""

    def __init__(
        self,
        config: TelegramConfig,
        transport: Optional[TelegramTransport] = None,
        max_attempts: int = DEFAULT_MAX_ATTEMPTS,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        if max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")
        if timeout <= 0:
            raise ValueError("timeout must be positive")
        self.config = config
        self.transport = transport or UrllibTelegramTransport()
        self.max_attempts = max_attempts
        self.timeout = timeout
        self.sleep = sleep

    def send(self, text: str) -> Mapping[str, Any]:
        if not text:
            raise TelegramError("Telegram message is empty")

        for attempt in range(1, self.max_attempts + 1):
            try:
                return self.transport.send_message(
                    self.config,
                    text,
                    self.timeout,
                )
            except TelegramRetryableError as exc:
                if attempt == self.max_attempts:
                    raise TelegramError(
                        "Telegram delivery failed after "
                        f"{self.max_attempts} attempts: {exc}"
                    ) from exc
                delay = (
                    exc.retry_after
                    if exc.retry_after is not None
                    else float(2 ** (attempt - 1))
                )
                self.sleep(max(delay, 0.0))

        raise TelegramError("Telegram delivery failed")


def send_brief(
    input_path: Path,
    client: TelegramBotClient,
) -> int:
    """Read, format, and send a brief. Return the number of messages sent."""
    try:
        markdown = input_path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise TelegramError(f"market brief not found: {input_path}") from exc

    messages = format_telegram_messages(markdown)
    for message in messages:
        client.send(message)
    return len(messages)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Send the generated AI Market Brief to Telegram."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_BRIEF_PATH,
        help=f"AI brief path (default: {DEFAULT_BRIEF_PATH})",
    )
    parser.add_argument(
        "--max-attempts",
        type=int,
        default=DEFAULT_MAX_ATTEMPTS,
        help=f"Attempts per message (default: {DEFAULT_MAX_ATTEMPTS})",
    )
    parser.add_argument(
        "--skip-if-unconfigured",
        action="store_true",
        help="Exit successfully when Telegram environment variables are absent.",
    )
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)

    try:
        config = TelegramConfig.from_environment()
    except TelegramError as exc:
        if args.skip_if_unconfigured:
            print("Telegram delivery skipped: secrets are not configured.")
            return 0
        print(f"Telegram configuration error: {exc}", file=sys.stderr)
        return 2

    try:
        client = TelegramBotClient(
            config=config,
            max_attempts=args.max_attempts,
        )
        message_count = send_brief(args.input, client)
    except (TelegramError, ValueError) as exc:
        print(f"Telegram delivery error: {exc}", file=sys.stderr)
        return 1

    print(f"Telegram delivery completed: {message_count} message(s) sent.")
    return 0


def cli() -> None:
    raise SystemExit(main())


def _decode_response(
    raw: bytes,
    allow_invalid: bool = False,
) -> Mapping[str, Any]:
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        if allow_invalid:
            return {}
        raise TelegramRetryableError(
            "Telegram returned an invalid response"
        ) from exc
    if not isinstance(payload, dict):
        if allow_invalid:
            return {}
        raise TelegramRetryableError("Telegram returned an invalid response")
    return payload


def _raise_api_error(
    payload: Mapping[str, Any],
    fallback_code: Optional[int] = None,
) -> None:
    raw_code = payload.get("error_code", fallback_code)
    code = raw_code if isinstance(raw_code, int) else fallback_code
    description = payload.get("description")
    safe_description = (
        description if isinstance(description, str) else "request was rejected"
    )
    retry_after = _read_retry_after(payload)
    message = (
        f"Telegram API error {code}: {safe_description}"
        if code is not None
        else f"Telegram API error: {safe_description}"
    )
    if code == 429 or (code is not None and code >= 500):
        raise TelegramRetryableError(message, retry_after=retry_after)
    raise TelegramError(message)


def _read_retry_after(payload: Mapping[str, Any]) -> Optional[float]:
    parameters = payload.get("parameters")
    if not isinstance(parameters, dict):
        return None
    retry_after = parameters.get("retry_after")
    if isinstance(retry_after, (int, float)) and retry_after >= 0:
        return float(retry_after)
    return None


if __name__ == "__main__":
    cli()

