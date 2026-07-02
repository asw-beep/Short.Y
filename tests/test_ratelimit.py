"""Rate-limiting tests (Phase 2, feature #2).

Limits are driven from `settings` via callables, so we monkeypatch them to small
values instead of hammering the endpoint hundreds of times. The `client` fixture
flushes the test Redis DB per test, so each test starts with empty buckets.
"""
from app.core.config import settings


def test_shorten_rate_limited(client, monkeypatch):
    monkeypatch.setattr(settings, "rate_limit_shorten", "2/minute")

    assert client.post("/shorten", json={"url": "https://a.com/1"}).status_code == 201
    assert client.post("/shorten", json={"url": "https://a.com/2"}).status_code == 201

    blocked = client.post("/shorten", json={"url": "https://a.com/3"})
    assert blocked.status_code == 429
    assert "rate limit exceeded" in blocked.json()["detail"].lower()
    # Clients rely on Retry-After to back off.
    assert "retry-after" in {k.lower() for k in blocked.headers}


def test_redirect_rate_limited(client, monkeypatch):
    monkeypatch.setattr(settings, "rate_limit_redirect", "3/minute")
    client.post("/shorten", json={"url": "https://example.com/dest"})

    for _ in range(3):
        assert client.get("/0000001", follow_redirects=False).status_code == 301

    blocked = client.get("/0000001", follow_redirects=False)
    assert blocked.status_code == 429


def test_limits_are_per_ip(client, monkeypatch):
    """A different client IP (via trusted X-Forwarded-For) gets its own bucket."""
    monkeypatch.setattr(settings, "rate_limit_shorten", "1/minute")
    monkeypatch.setattr(settings, "trust_proxy", True)

    h1 = {"X-Forwarded-For": "203.0.113.1"}
    h2 = {"X-Forwarded-For": "203.0.113.2"}

    assert client.post("/shorten", json={"url": "https://a.com/1"}, headers=h1).status_code == 201
    # Same IP again → blocked.
    assert client.post("/shorten", json={"url": "https://a.com/2"}, headers=h1).status_code == 429
    # Different IP → still allowed.
    assert client.post("/shorten", json={"url": "https://a.com/3"}, headers=h2).status_code == 201


def test_xrealip_beats_spoofed_xff(client, monkeypatch):
    """Behind a trusted proxy, the unspoofable X-Real-IP is the bucket key even
    when the client injects a different left-most X-Forwarded-For."""
    monkeypatch.setattr(settings, "rate_limit_shorten", "1/minute")
    monkeypatch.setattr(settings, "trust_proxy", True)

    # Real client is 10.0.0.7 (set by the proxy); the client tries to look like
    # a fresh IP each request via XFF — it must not get a fresh bucket.
    h_real = {"X-Real-IP": "10.0.0.7", "X-Forwarded-For": "1.1.1.1"}
    h_spoof = {"X-Real-IP": "10.0.0.7", "X-Forwarded-For": "2.2.2.2"}

    assert client.post("/shorten", json={"url": "https://a.com/1"}, headers=h_real).status_code == 201
    assert client.post("/shorten", json={"url": "https://a.com/2"}, headers=h_spoof).status_code == 429


def test_spoofed_xff_ignored_when_proxy_untrusted(client, monkeypatch):
    """With trust_proxy off, XFF is ignored so all requests share the peer bucket."""
    monkeypatch.setattr(settings, "rate_limit_shorten", "1/minute")
    monkeypatch.setattr(settings, "trust_proxy", False)

    assert client.post(
        "/shorten", json={"url": "https://a.com/1"}, headers={"X-Forwarded-For": "203.0.113.9"}
    ).status_code == 201
    # A "different" spoofed XFF must NOT get a fresh bucket.
    assert client.post(
        "/shorten", json={"url": "https://a.com/2"}, headers={"X-Forwarded-For": "203.0.113.8"}
    ).status_code == 429
