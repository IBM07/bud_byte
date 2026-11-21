import httpx


async def test_healthz_is_always_ok(client: httpx.AsyncClient) -> None:
    r = await client.get("/healthz")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert "version" in body


async def test_readyz_fails_when_database_not_configured(client: httpx.AsyncClient) -> None:
    r = await client.get("/readyz")
    assert r.status_code == 503
    checks = r.json()["checks"]
    assert checks["redis"] == "ok"
    assert checks["database"] == "not_configured"


async def test_openapi_is_served(client: httpx.AsyncClient) -> None:
    r = await client.get("/openapi.json")
    assert r.status_code == 200
    assert "/healthz" in r.json()["paths"]
