import os
import subprocess
import sys
import time
import logging
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
import asyncio

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add backend to path
root_dir = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(root_dir))

try:
    from backend.app.core.config import settings
    from backend.app.core.database_url import normalize_database_url
except ImportError as e:
    logger.error(f"Failed to import settings: {e}")
    # Fallback import
    import importlib.util
    spec = importlib.util.spec_from_file_location("config", root_dir / "backend" / "app" / "core" / "config.py")
    config_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(config_module)
    settings = config_module.settings


async def wait_for_database() -> None:
    """Wait for database to be ready with retry logic."""
    try:
        database_url = normalize_database_url(settings.effective_database_url)
        logger.info(f"Connecting to database...")
    except Exception as e:
        logger.error(f"Failed to get database URL: {e}")
        # Try direct connection
        database_url = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:password@localhost:5432/astrocycle")
        logger.info(f"Using fallback database URL")
    
    engine = create_async_engine(database_url, pool_pre_ping=True)
    delay_seconds = 2
    max_attempts = 30

    for attempt in range(1, max_attempts + 1):
        try:
            async with engine.connect() as connection:
                await connection.execute(text("SELECT 1"))
            await engine.dispose()
            logger.info("Database connection ready.")
            return
        except Exception as exc:
            if attempt == max_attempts:
                await engine.dispose()
                logger.error(f"Database connection failed after {max_attempts} attempts")
                raise
            logger.warning(f"Waiting for database ({attempt}/{max_attempts}): {exc}")
            time.sleep(delay_seconds)


def run_migrations() -> None:
    """Run database migrations."""
    root_dir = Path(__file__).resolve().parents[2]
    env = os.environ.copy()
    existing_pythonpath = env.get("PYTHONPATH")
    env["PYTHONPATH"] = (
        str(root_dir)
        if not existing_pythonpath
        else f"{root_dir}{os.pathsep}{existing_pythonpath}"
    )

    logger.info("Running database migrations...")
    try:
        subprocess.run(
            ["alembic", "-c", "backend/alembic.ini", "upgrade", "head"],
            cwd=root_dir,
            env=env,
            check=True,
        )
        logger.info("Migrations completed successfully.")
    except subprocess.CalledProcessError as e:
        logger.error(f"Migration failed: {e}")
        # Continue anyway - might be already migrated
        logger.info("Continuing despite migration error...")


def start_server() -> None:
    """Start the uvicorn server."""
    port = os.getenv("PORT", "8000")
    logger.info(f"Starting server on port {port}...")
    
    # Use subprocess instead of execvp for better error handling
    try:
        subprocess.run(
            [
                "uvicorn",
                "backend.app.main:app",
                "--host", "0.0.0.0",
                "--port", port,
                "--proxy-headers",
                "--forwarded-allow-ips", "*",
            ],
            check=True,
        )
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}")
        raise


def main() -> None:
    """Main startup function."""
    logger.info("Starting AstroCycle backend...")
    logger.info(f"Python path: {sys.path}")
    logger.info(f"Working directory: {os.getcwd()}")
    
    # Check environment
    logger.info(f"RAILWAY_ENVIRONMENT: {os.getenv('RAILWAY_ENVIRONMENT', 'not set')}")
    logger.info(f"PORT: {os.getenv('PORT', '8000')}")
    
    asyncio.run(wait_for_database())
    run_migrations()
    start_server()


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        logger.error(f"Startup failed: {exc}", exc_info=True)
        sys.exit(1)
