import redis

from app.core.config import settings

# Namespaced so rate-limit keys (Phase 2, feature #2) won't collide.
KEY_PREFIX = "url:"

# Sentinel stored for a known-missing code, so 404 enumeration scans are
# absorbed by Redis instead of hitting Postgres on every request.
NEGATIVE = "\x00"

_pool: redis.ConnectionPool | None = None


def init_pool() -> None:
    """Create the shared connection pool. Called from the app lifespan."""
    global _pool
    if _pool is None:
        _pool = redis.ConnectionPool.from_url(settings.redis_url, decode_responses=True)


def close_pool() -> None:
    global _pool
    if _pool is not None:
        _pool.disconnect()
        _pool = None


def get_client() -> redis.Redis:
    if _pool is None:
        init_pool()
    return redis.Redis(connection_pool=_pool)


def get_cache() -> redis.Redis:
    """FastAPI dependency. Overridden in tests to point at a separate DB index."""
    return get_client()


def cache_key(code: str) -> str:
    return f"{KEY_PREFIX}{code}"
