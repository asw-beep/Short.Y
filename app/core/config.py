from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql://shortener:shortener@localhost:5432/shortener"
    base_url: str = "http://localhost:8000"
    redis_url: str = "redis://localhost:6379/0"
    cache_ttl_seconds: int = 3600
    cache_negative_ttl_seconds: int = 60

    # Rate limiting (Phase 2). Per-IP, moving-window. Tune per environment.
    rate_limit_shorten: str = "30/minute"
    rate_limit_redirect: str = "120/minute"
    # Only trust X-Forwarded-For when fronted by a proxy we control (Phase 3 Nginx).
    trust_proxy: bool = False

    # Observability
    log_level: str = "INFO"
    log_json: bool = True  # JSON in prod; set false for human-readable dev logs

    # Analytics (Redis Stream + worker)
    analytics_stream_maxlen: int = 100_000  # approx cap so an offline worker can't OOM Redis

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)


settings = Settings()
