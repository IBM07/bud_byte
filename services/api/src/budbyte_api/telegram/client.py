"""Minimal async Telegram Bot API client."""

from __future__ import annotations

from types import TracebackType
from typing import Any, Self

import httpx

API_BASE = "https://api.telegram.org"


class TelegramError(RuntimeError):
    pass


class TelegramClient:
    def __init__(self, token: str, *, timeout: float = 10.0) -> None:
        self._token = token
        self._http = httpx.AsyncClient(base_url=f"{API_BASE}/bot{token}", timeout=timeout)

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        await self._http.aclose()

    async def call(self, method: str, payload: dict[str, Any]) -> Any:
        resp = await self._http.post(f"/{method}", json=payload)
        data: dict[str, Any] = resp.json()
        if not data.get("ok"):
            # Never include the token-bearing URL in the error.
            raise TelegramError(f"{method} failed: {data.get('description', resp.status_code)}")
        return data.get("result")

    async def send_message(self, chat_id: int, text: str) -> Any:
        return await self.call("sendMessage", {"chat_id": chat_id, "text": text})

    async def set_webhook(self, url: str, secret_token: str) -> Any:
        return await self.call(
            "setWebhook",
            {
                "url": url,
                "secret_token": secret_token,
                "allowed_updates": ["message", "callback_query"],
                "drop_pending_updates": True,
            },
        )
