from backend.app.core.database_url import normalize_database_url


def test_normalize_postgres_scheme_for_asyncpg():
    assert (
        normalize_database_url("postgres://user:pass@example.com:5432/db")
        == "postgresql+asyncpg://user:pass@example.com:5432/db"
    )


def test_normalize_postgresql_scheme_for_asyncpg():
    assert (
        normalize_database_url("postgresql://user:pass@example.com:5432/db")
        == "postgresql+asyncpg://user:pass@example.com:5432/db"
    )


def test_convert_sslmode_require_to_asyncpg_ssl():
    assert (
        normalize_database_url("postgresql://user:pass@example.com:5432/db?sslmode=require")
        == "postgresql+asyncpg://user:pass@example.com:5432/db?ssl=true"
    )
