# BudByte task runner. `just` lists recipes.
set windows-shell := ["powershell.exe", "-NoLogo", "-NoProfile", "-Command"]

default:
    @just --list

# Install all Python + JS dependencies
setup:
    uv sync --all-packages
    pnpm install

# Everything CI runs that doesn't need Docker or network services
check: lint typecheck test web-build gen-check

lint:
    uv run ruff check .
    uv run ruff format --check .
    pnpm lint

fmt:
    uv run ruff format .
    uv run ruff check . --fix

typecheck:
    uv run pyright
    pnpm typecheck

# Python unit tests (integration tests auto-skip without BUDBYTE_TEST_* env)
test:
    uv run pytest -q

# Python integration tests against real Postgres + Redis
test-integration:
    uv run pytest -q -m integration

web-build:
    pnpm --filter @budbyte/web build

# Playwright smoke (builds the web app, uses a mock API)
e2e:
    pnpm --filter @budbyte/web test:e2e

# Regenerate the OpenAPI schema and the typed TS client
gen:
    uv run budbyte-openapi packages/api-client/openapi.json
    pnpm --filter @budbyte/api-client gen

# Fail if generated files are stale (used by CI)
gen-check: gen
    git diff --exit-code -- packages/api-client

# Run the API locally (needs Postgres + Redis, see infra/compose.yml)
dev-api:
    uv run budbyte-api

dev-worker:
    uv run budbyte-worker

dev-web:
    pnpm --filter @budbyte/web dev

docker-build:
    docker build -f infra/Dockerfile -t budbyte-api .
