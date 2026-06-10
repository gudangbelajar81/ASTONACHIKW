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
    
    # AI Provider Configuration - Add all new providers
    AI_PROVIDER_ORDER: str = "kie,openai,gemini,deepseek,xai,deepseek_v3,qwen_coder,mistral,claude_sonnet,gpt5,kimi,kimi_free,qwen_coder_free,gemma,gpt5_o3"
    
    # KIE AI Configuration
    KIE_API_KEY: str = ""
    KIE_MODEL: str = "claude-opus-4-6"
    
    # OpenAI Configuration
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"
    
    # Google Gemini Configuration
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.5-flash"
    
    # DeepSeek Configuration
    DEEPSEEK_API_KEY: str = ""
    DEEPSEEK_MODEL: str = "deepseek-chat"
    
    # DeepSeek V3 Configuration
    DEEPSEEK_V3_API_KEY: str = ""
    DEEPSEEK_V3_MODEL: str = "deepseek-v3"
    
    # xAI (Grok) Configuration
    XAI_API_KEY: str = ""
    XAI_MODEL: str = "grok-4.3"
    
    # Qwen Coder Configuration
    QWEN_CODER_API_KEY: str = ""
    QWEN_CODER_MODEL: str = "qwen-coder"
    
    # Mistral Configuration
    MISTRAL_API_KEY: str = ""
    MISTRAL_MODEL: str = "mistral-medium-3.5"
    
    # Claude Sonnet Configuration
    CLAUDE_SONNET_API_KEY: str = ""
    CLAUDE_SONNET_MODEL: str = "claude-sonnet-4.6"
    
    # GPT-5 Configuration
    GPT5_API_KEY: str = ""
    GPT5_MODEL: str = "gpt-5"
    
    # Kimi Configuration
    KIMI_API_KEY: str = ""
    KIMI_MODEL: str = "kimi-k2.6"
    
    # Kimi Free Configuration
    KIMI_FREE_API_KEY: str = ""
    KIMI_FREE_MODEL: str = "kimi-k2.6-free"
    
    # Qwen Coder Free Configuration
    QWEN_CODER_FREE_API_KEY: str = ""
    QWEN_CODER_FREE_MODEL: str = "qwen-coder-free"
    
    # Gemma Configuration
    GEMMA_API_KEY: str = ""
    GEMMA_MODEL: str = "gemma-4-31b-free"
    
    # GPT-5 o3 Configuration
    GPT5_O3_API_KEY: str = ""
    GPT5_O3_MODEL: str = "gpt-5-o3"

    # ── Data Provider: EODHD (Intraday + EOD) ──
    EODHD_API_KEY: str = ""
    # Exchange default untuk IDX Indonesia
    EODHD_EXCHANGE: str = "JK"
    # Aktifkan EODHD sebagai sumber data intraday (1m/5m/15m/30m/1h/4h)
    EODHD_ENABLED: bool = True

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