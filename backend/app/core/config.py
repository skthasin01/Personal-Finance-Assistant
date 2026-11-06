"""Application settings loaded from environment variables / .env file.

Every secret (database password, JWT secret, LLM API key) lives here and is read
from the environment only. Nothing in this module is ever sent to the frontend.
"""
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "AI Personal Finance Assistant"
    environment: str = Field(default="development", description="development | production | test")
    api_prefix: str = "/api/v1"

    # Database
    database_url: str = "postgresql+psycopg://finance_user:change_me@localhost:5432/finance_db"
    sql_echo: bool = False

    # Auth
    jwt_secret_key: str = "dev-only-change-me-to-a-long-random-string"
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 15
    refresh_token_days: int = 7
    # Refresh cookie: Secure must be True in production (HTTPS)
    cookie_secure: bool = False
    cookie_samesite: str = "strict"

    # CORS: comma-separated list of trusted frontend origins
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    # Demo mode: one-click, temporary demo workspaces (keep false in production)
    demo_mode: bool = False
    demo_ttl_hours: int = 24

    # Rate limits (requests per minute per client)
    auth_rate_limit_per_minute: int = 10
    ai_rate_limit_per_minute: int = 10

    # AI provider: "anthropic" or "local" (rule-based, no external calls)
    llm_provider: str = "local"
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-opus-5-5"
    anthropic_effort: str = "low"
    llm_timeout_seconds: float = 30.0
    llm_max_tokens: int = 4000

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    if settings.is_production:
        if settings.jwt_secret_key.startswith("dev-only") or len(settings.jwt_secret_key) < 32:
            raise RuntimeError("JWT_SECRET_KEY must be a strong secret in production")
        if not settings.cookie_secure:
            raise RuntimeError("COOKIE_SECURE must be true in production")
    return settings
