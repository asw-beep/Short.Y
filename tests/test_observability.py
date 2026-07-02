"""Observability tests (Phase 2): readiness health check + request IDs."""
import redis

from app.core.cache import get_cache
from app.main import app


def test_livez_is_static(client):
    r = client.get("/livez")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_health_reports_dependencies(client):
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["checks"] == {"database": "ok", "redis": "ok"}


def test_health_degraded_when_redis_down(client):
    class BrokenRedis:
        def ping(self):
            raise redis.ConnectionError("redis down")

    app.dependency_overrides[get_cache] = lambda: BrokenRedis()
    try:
        r = client.get("/health")
        assert r.status_code == 503
        body = r.json()
        assert body["status"] == "degraded"
        assert body["checks"]["redis"] == "down"
        assert body["checks"]["database"] == "ok"
    finally:
        app.dependency_overrides.pop(get_cache, None)


def test_request_id_header_present(client):
    r = client.get("/livez")
    assert r.headers.get("x-request-id")


def test_request_id_is_echoed_when_provided(client):
    r = client.get("/livez", headers={"X-Request-ID": "trace-abc-123"})
    assert r.headers["x-request-id"] == "trace-abc-123"
