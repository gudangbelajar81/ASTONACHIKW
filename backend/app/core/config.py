import os
from urllib.parse import quote_plus
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    DATABASE_URL: str = ""
    PGHOST: str = ""
    PGPORT: str = "5432"
    PGDATABASE: str = ""
    PGUSER: str = ""
    PGPASSWORD: str = ""
    SECRET_KEY: str = "change-this-secret-key"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    ALGORITHM: str = "HS256"
    FRONTEND_URL: str = "http://localhost:3000"
    BACKEND_URL: str = "http://localhost:8000"
    SWISSEPH_PATH: str = "./ephemeris"
    AI_PROVIDER_ORDER: str = "openai,gemini,deepseek,xai"
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.5-flash"
    DEEPSEEK_API_KEY: str = ""
    DEEPSEEK_MODEL: str = "deepseek-chat"
    XAI_API_KEY: str = ""
    XAI_MODEL: str = "grok-4.3"

    @property
    def effective_database_url(self) -> str:
        is_railway = bool(os.getenv("RAILWAY_ENVIRONMENT") or os.getenv("RAILWAY_PROJECT_ID"))
        if self.DATABASE_URL and not (is_railway and "localhost" in self.DATABASE_URL):
            return self.DATABASE_URL
        if self.PGHOST and self.PGDATABASE and self.PGUSER:
            password = quote_plus(self.PGPASSWORD)
            return (
                f"postgresql+asyncpg://{self.PGUSER}:{password}"
                f"@{self.PGHOST}:{self.PGPORT}/{self.PGDATABASE}"
            )
        if is_railway:
            raise ValueError(
                "Railway database is not configured. Add DATABASE_URL as a variable reference "
                "to the Postgres service, for example ${{Postgres.DATABASE_URL}}."
            )
        return "postgresql+asyncpg://postgres:password@localhost:5432/astrocycle"


settings = Settings()
