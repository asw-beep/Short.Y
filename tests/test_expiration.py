"""Expiration policy tests (Phase 2): create with expiry, 410 on expired."""
from datetime import datetime, timedelta, timezone

import pytest

from app.core.cache import EXPIRED, cache_key
from app.models.url import URL
from app.services import shortener
from app.services.shortener import URLExpiredError


def _future(minutes=60):
    return datetime.now(timezone.utc) + timedelta(minutes=minutes)


def _past(minutes=60):
    return datetime.now(timezone.utc) - timedelta(minutes=minutes)


def test_shorten_with_future_expiry(client):
    r = client.post(
        "/shorten",
        json={"url": "https://example.com/", "expires_at": _future().isoformat()},
    )
    assert r.status_code == 201
    assert r.json()["expires_at"] is not None


def test_shorten_rejects_past_expiry(client):
    r = client.post(
        "/shorten",
        json={"url": "https://example.com/", "expires_at": _past().isoformat()},
    )
    assert r.status_code == 422


def test_future_expiry_still_redirects(client):
    client.post(
        "/shorten",
        json={"url": "https://example.com/live", "expires_at": _future().isoformat()},
    )
    r = client.get("/0000001", follow_redirects=False)
    assert r.status_code == 301
    assert r.headers["location"] == "https://example.com/live"


def test_expired_link_returns_410_and_caches_sentinel(client, db_session, cache_client):
    # Insert an already-expired mapping directly (the API won't create one).
    db_session.add(
        URL(short_code="gone123", long_url="https://old.example/", is_custom=True, expires_at=_past())
    )
    db_session.commit()

    r = client.get("/gone123", follow_redirects=False)
    assert r.status_code == 410
    # Second hit is served straight from the cache sentinel (no DB).
    assert cache_client.get(cache_key("gone123")) == EXPIRED
    assert client.get("/gone123", follow_redirects=False).status_code == 410


def test_expired_sentinel_short_circuits(client, cache_client):
    cache_client.set(cache_key("phantom"), EXPIRED)
    assert client.get("/phantom", follow_redirects=False).status_code == 410


def test_resolve_raises_for_expired(db_session, cache_client):
    db_session.add(
        URL(short_code="svc-exp", long_url="https://x/", is_custom=True, expires_at=_past())
    )
    db_session.commit()
    with pytest.raises(URLExpiredError):
        shortener.resolve_long_url(db_session, cache_client, "svc-exp")
