import ssl

import pytest
from pydantic import SecretStr, ValidationError

from budbyte_api.db import to_asyncpg_url
from budbyte_api.settings import Settings


def test_neon_style_url_is_converted_for_asyncpg() -> None:
    url, connect_args = to_asyncpg_url(
        "postgresql://user:pw@ep-x.neon.tech/db?sslmode=require&channel_binding=require"
    )
    assert url == "postgresql+asyncpg://user:pw@ep-x.neon.tech/db"
    assert connect_args == {"ssl": "require"}  # direct (non-pooled) host


def test_plain_postgres_scheme_without_ssl() -> None:
    url, connect_args = to_asyncpg_url("postgres://u:p@localhost:5432/budbyte")
    assert url == "postgresql+asyncpg://u:p@localhost:5432/budbyte"
    assert connect_args == {}


def test_production_requires_telegram_secrets() -> None:
    with pytest.raises(ValidationError):
        Settings(environment="production", telegram_bot_token=SecretStr("1:a"))


def test_secrets_are_not_leaked_in_repr() -> None:
    s = Settings(environment="test", telegram_bot_token=SecretStr("123:supersecret"))
    assert "supersecret" not in repr(s)


def test_pooled_neon_url_disables_asyncpg_statement_cache() -> None:
    _url, connect_args = to_asyncpg_url(
        "postgresql://u:p@ep-x-pooler.eu-central-1.aws.neon.tech/db?sslmode=require"
    )
    assert connect_args["statement_cache_size"] == 0
    # SQLAlchemy's asyncpg adapter keeps its own statement cache on top of asyncpg's.
    assert connect_args["prepared_statement_cache_size"] == 0
    assert callable(connect_args["prepared_statement_name_func"])


@pytest.mark.parametrize(("mode", "check_hostname"), [("verify-full", True), ("verify-ca", False)])
def test_certificate_verifying_sslmodes_are_not_downgraded(mode: str, check_hostname: bool) -> None:
    # Our own context on the system CA store: asyncpg's string modes demand ~/.postgresql/root.crt.
    _url, connect_args = to_asyncpg_url(f"postgresql://u:p@db.example.com/db?sslmode={mode}")
    ctx = connect_args["ssl"]
    assert isinstance(ctx, ssl.SSLContext)
    assert ctx.verify_mode == ssl.CERT_REQUIRED
    assert ctx.check_hostname is check_hostname


def test_require_with_sslrootcert_verifies_the_ca_like_libpq() -> None:
    # libpq: sslmode=require plus an available root cert behaves like verify-ca.
    url, connect_args = to_asyncpg_url("postgresql://u:p@h/db?sslmode=require&sslrootcert=system")
    assert "sslrootcert" not in url
    ctx = connect_args["ssl"]
    assert isinstance(ctx, ssl.SSLContext)
    assert ctx.verify_mode == ssl.CERT_REQUIRED
    assert ctx.check_hostname is False


def test_unknown_sslmode_fails_loudly_instead_of_downgrading() -> None:
    with pytest.raises(ValueError, match="sslmode"):
        to_asyncpg_url("postgresql://u:p@h/db?sslmode=verify_full")  # typo for verify-full


def test_blank_env_values_are_treated_as_unset() -> None:
    s = Settings(
        environment="test",
        database_url="",  # pyright: ignore[reportArgumentType]
        sentry_dsn="  ",  # pyright: ignore[reportArgumentType]
        redis_url="",  # pyright: ignore[reportArgumentType]
    )
    assert s.database_url is None
    assert s.sentry_dsn is None
    assert s.redis_url.get_secret_value() == "redis://localhost:6379/0"


def test_production_rejects_blank_required_secrets() -> None:
    with pytest.raises(ValidationError):
        Settings(
            environment="production",
            database_url="",  # pyright: ignore[reportArgumentType]
            telegram_bot_token="",  # pyright: ignore[reportArgumentType]
            telegram_webhook_secret="",  # pyright: ignore[reportArgumentType]
            telegram_path_secret="",  # pyright: ignore[reportArgumentType]
        )


def test_tests_do_not_read_the_local_dotenv() -> None:
    assert Settings.model_config.get("env_file") is None
