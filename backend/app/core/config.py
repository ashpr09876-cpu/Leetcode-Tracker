from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    env: str = "development"
    database_url: str = "postgresql+psycopg://codetrack:CHANGE_ME@localhost:5432/codetrack"
    redis_url: str = "redis://localhost:6379/0"
    secret_key: str = "CHANGE_ME_TO_A_LONG_RANDOM_STRING"
    access_token_minutes: int = 15
    refresh_token_days: int = 14
    cors_origins: str = "http://localhost:5173"
    frontend_url: str = "http://localhost:5173"
    cookie_secure: bool = False
    admin_email: str = ""

    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:8000/api/v1/auth/google/callback"

    ai_provider: str = ""
    gemini_api_key: str = ""
    gemini_model: str = "gemini-1.5-flash"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-3-5-haiku-latest"
    ollama_base_url: str = ""
    ollama_model: str = "llama3.1"
    ai_daily_limit: int = 50
    ai_timeout_seconds: float = 60.0

    @property
    def cors_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    s = Settings()
    if s.env == "production" and s.secret_key.startswith("CHANGE_ME"):
        raise RuntimeError("SECRET_KEY must be set to a strong random value in production")
    return s
