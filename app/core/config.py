import os

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_DEFAULT_BASE_URL = "http://localhost:8000"


class Settings(BaseSettings):
    database_url: str = "postgresql://shortener:shortener@localhost:5432/shortener"
    base_url: str = _DEFAULT_BASE_URL
    redis_url: str = "redis://localhost:6379/0"
    cache_ttl_seconds: int = 3600
    cache_negative_ttl_seconds: int = 60

    # Rate limiting (Phase 2). Per-IP, moving-window. Tune per environment.
    rate_limit_shorten: str = "30/minute"
    rate_limit_redirect: str = "120/minute"
    rate_limit_list: str = "60/minute"
    # Only trust X-Forwarded-For when fronted by a proxy we control (Phase 3 Nginx).
    trust_proxy: bool = False

    # Observability
    log_level: str = "INFO"
    log_json: bool = True  # JSON in prod; set false for human-readable dev logs

    # Analytics (Redis Stream + worker)
    analytics_stream_maxlen: int = 100_000  # approx cap so an offline worker can't OOM Redis
    # Run the analytics drain loop inside the web process instead of a separate
    # worker container. Off by default (Docker Compose runs a real worker
    # service); Render's free-tier deployment enables this since free Background
    # Workers aren't available at all there. See ADR-013.
    enable_inprocess_worker: bool = False

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)

    @model_validator(mode="after")
    def _default_base_url_from_render(self) -> "Settings":
        """If BASE_URL was never explicitly set, adopt Render's auto-injected
        RENDER_EXTERNAL_URL (e.g. https://shorty-api.onrender.com) so shortened
        links reflect the real deployed host instead of the localhost default
        (see ADR-013). An explicit BASE_URL env var — e.g. after attaching a
        custom domain — always takes precedence over this fallback.
        """
        if self.base_url == _DEFAULT_BASE_URL:
            render_url = os.environ.get("RENDER_EXTERNAL_URL")
            if render_url:
                self.base_url = render_url
        return self


settings = Settings()
