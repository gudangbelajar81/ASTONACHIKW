from urllib.parse import quote_plus
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
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
    OPENAI_API_KEY: str = ""

    @property
    def effective_database_url(self) -> str:
        if self.DATABASE_URL:
            return self.DATABASE_URL
        if self.PGHOST and self.PGDATABASE and self.PGUSER:
            password = quote_plus(self.PGPASSWORD)
            return (
                f"postgresql+asyncpg://{self.PGUSER}:{password}"
                f"@{self.PGHOST}:{self.PGPORT}/{self.PGDATABASE}"
            )
        return "postgresql+asyncpg://postgres:password@localhost:5432/astrocycle"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
