import redis

from app.core.cache import NEGATIVE, cache_key, get_cache
from app.main import app


def test_redirect_populates_cache(client, cache_client):
    client.post("/shorten", json={"url": "https://example.com/x"})
    assert cache_client.get(cache_key("0000001")) is None

    r = client.get("/0000001", follow_redirects=False)
    assert r.status_code == 301
    assert cache_client.get(cache_key("0000001")) == "https://example.com/x"


def test_redirect_served_from_cache_without_db(client, cache_client):
    # Seed cache for a code that does not exist in the DB. A DB-only lookup
    # would 404; serving it proves the cache short-circuits Postgres.
    cache_client.set(cache_key("manual"), "https://cached.example/")
    r = client.get("/manual", follow_redirects=False)
    assert r.status_code == 301
    assert r.headers["location"] == "https://cached.example/"


def test_negative_caching_on_miss(client, cache_client):
    r = client.get("/nope", follow_redirects=False)
    assert r.status_code == 404
    assert cache_client.get(cache_key("nope")) == NEGATIVE


def test_negative_cache_short_circuits(client, cache_client):
    cache_client.set(cache_key("ghost"), NEGATIVE)
    r = client.get("/ghost", follow_redirects=False)
    assert r.status_code == 404


def test_redis_down_fails_closed(client):
    class BrokenRedis:
        def get(self, *args, **kwargs):
            raise redis.ConnectionError("redis down")

        def set(self, *args, **kwargs):
            raise redis.ConnectionError("redis down")

    app.dependency_overrides[get_cache] = lambda: BrokenRedis()
    try:
        r = client.get("/anything", follow_redirects=False)
        assert r.status_code == 503
    finally:
        app.dependency_overrides.pop(get_cache, None)
