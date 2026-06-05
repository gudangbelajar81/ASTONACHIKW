import os
import subprocess
import sys
import time

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
import asyncio

from backend.app.core.config import settings
from backend.app.core.database_url import normalize_database_url


async def wait_for_database() -> None:
    database_url = normalize_database_url(str(settings.DATABASE_URL))
    engine = create_async_engine(database_url, pool_pre_ping=True)
    delay_seconds = 2
    max_attempts = 30

    for attempt in range(1, max_attempts + 1):
        try:
            async with engine.connect() as connection:
                await connection.execute(text("SELECT 1"))
            await engine.dispose()
            print("Database connection ready.")
            return
        except Exception as exc:
            if attempt == max_attempts:
                await engine.dispose()
                raise
            print(f"Waiting for database ({attempt}/{max_attempts}): {exc}")
            time.sleep(delay_seconds)


def run_migrations() -> None:
    subprocess.run(
        ["alembic", "-c", "backend/alembic.ini", "upgrade", "head"],
        check=True,
    )


def start_server() -> None:
    port = os.getenv("PORT", "8000")
    os.execvp(
        "uvicorn",
        [
            "uvicorn",
            "backend.app.main:app",
            "--host",
            "0.0.0.0",
            "--port",
            port,
        ],
    )


def main() -> None:
    asyncio.run(wait_for_database())
    run_migrations()
    start_server()


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Startup failed: {exc}", file=sys.stderr)
        raise
