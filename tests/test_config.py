"""BASE_URL auto-detection from Render's RENDER_EXTERNAL_URL (ADR-013)."""
from app.core.config import Settings


def test_base_url_defaults_to_localhost_without_render(monkeypatch):
    monkeypatch.delenv("RENDER_EXTERNAL_URL", raising=False)
    monkeypatch.delenv("BASE_URL", raising=False)
    s = Settings(_env_file=None)
    assert s.base_url == "http://localhost:8000"


def test_base_url_adopts_render_external_url_when_unset(monkeypatch):
    monkeypatch.delenv("BASE_URL", raising=False)
    monkeypatch.setenv("RENDER_EXTERNAL_URL", "https://shorty-api.onrender.com")
    s = Settings(_env_file=None)
    assert s.base_url == "https://shorty-api.onrender.com"


def test_explicit_base_url_wins_over_render_external_url(monkeypatch):
    monkeypatch.setenv("BASE_URL", "https://shorty.example.dev")
    monkeypatch.setenv("RENDER_EXTERNAL_URL", "https://shorty-api.onrender.com")
    s = Settings(_env_file=None)
    assert s.base_url == "https://shorty.example.dev"
