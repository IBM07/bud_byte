"""Console entry points (see [project.scripts])."""

from __future__ import annotations

import asyncio
import json
import os
import sys

import structlog

from budbyte_api.logging import configure_logging
from budbyte_api.settings import Settings, secret

log = structlog.get_logger()


def serve() -> None:
    import uvicorn

    uvicorn.run(
        "budbyte_api.main:app_factory",
        factory=True,
        host="0.0.0.0",  # noqa: S104 - container entrypoint
        port=int(os.environ.get("PORT", "8000")),
        proxy_headers=True,
        forwarded_allow_ips="*",
        log_config=None,
    )


def worker() -> None:
    from budbyte_api.worker import main

    main()


def cron() -> None:
    """``budbyte-cron <nightly|maint>``. Phase 1: logged no-ops wired to Northflank cron jobs."""
    settings = Settings()
    configure_logging(settings.log_level)
    job = sys.argv[1] if len(sys.argv) > 1 else ""
    if job not in ("nightly", "maint"):
        print("usage: budbyte-cron <nightly|maint>", file=sys.stderr)
        raise SystemExit(2)
    log.info("cron.run", job=job, note="no-op until Phase 3/7")


def export_openapi() -> None:
    """``budbyte-openapi [path]``: write the OpenAPI schema (used by `just gen`)."""
    from budbyte_api.main import create_app

    app = create_app(Settings(environment="test"))
    schema = json.dumps(app.openapi(), indent=2, sort_keys=True) + "\n"
    if len(sys.argv) > 1:
        with open(sys.argv[1], "w", encoding="utf-8", newline="\n") as fh:
            fh.write(schema)
    else:
        sys.stdout.write(schema)


def set_webhook() -> None:
    """``budbyte-set-webhook <public-base-url>``: point Telegram at this deployment."""
    from budbyte_api.telegram.client import TelegramClient

    settings = Settings()
    if len(sys.argv) < 2:
        print("usage: budbyte-set-webhook https://api.example.com", file=sys.stderr)
        raise SystemExit(2)
    token = secret(settings.telegram_bot_token)
    path = secret(settings.telegram_path_secret)
    header = secret(settings.telegram_webhook_secret)
    if not (token and path and header):
        raise SystemExit("telegram token, path secret and webhook secret must be set")
    url = f"{sys.argv[1].rstrip('/')}/tg/webhook/{path}"

    async def _go() -> None:
        async with TelegramClient(token) as tg:
            await tg.set_webhook(url, header)

    asyncio.run(_go())
    print("webhook set")
