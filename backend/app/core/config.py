from pydantic import AnyUrl
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: AnyUrl = "postgresql+asyncpg://postgres:password@localhost:5432/astrocycle"
    SECRET_KEY: str = "change-this-secret-key"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    ALGORITHM: str = "HS256"
    FRONTEND_URL: str = "http://localhost:3000"
    BACKEND_URL: str = "http://localhost:8000"
    OPENAI_API_KEY: str = ""

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
