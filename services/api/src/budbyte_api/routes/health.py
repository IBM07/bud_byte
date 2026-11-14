"""Liveness and readiness probes."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import Literal

from fastapi import APIRouter, Request, Response
from pydantic import BaseModel

from budbyte_api import __version__

router = APIRouter(tags=["health"])

CheckResult = Literal["ok", "error", "timeout", "not_configured"]
Check = Callable[[], Awaitable[None]] | None


class Health(BaseModel):
    status: Literal["ok"]
    version: str


class Readiness(BaseModel):
    status: Literal["ok", "degraded"]
    checks: dict[str, CheckResult]


@router.get("/healthz", response_model=Health)
async def healthz() -> Health:
    """Liveness: the process is up. Never touches dependencies."""
    return Health(status="ok", version=__version__)


CHECK_TIMEOUT_SECONDS = 2.0


async def _run(check: Check) -> CheckResult:
    if check is None:
        return "not_configured"
    try:
        async with asyncio.timeout(CHECK_TIMEOUT_SECONDS):
            await check()
    except TimeoutError:
        return "timeout"
    except Exception:
        return "error"
    return "ok"


@router.get("/readyz", response_model=Readiness, responses={503: {"model": Readiness}})
async def readyz(request: Request, response: Response) -> Readiness:
    """Readiness: dependencies (Postgres, Redis) are reachable."""
    checks: dict[str, Check] = request.app.state.readiness_checks
    names = list(checks)
    results = await asyncio.gather(*(_run(checks[n]) for n in names))
    out: dict[str, CheckResult] = dict(zip(names, results, strict=True))
    ok = all(v == "ok" for v in out.values())
    if not ok:
        response.status_code = 503
    return Readiness(status="ok" if ok else "degraded", checks=out)
