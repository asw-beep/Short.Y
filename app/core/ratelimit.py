"""Per-route rate limiting (Phase 2, feature #2).

Uses SlowAPI on top of a Redis storage backend so limits are enforced
consistently across every FastAPI worker/replica (an in-process limiter would
reset per worker and be trivially bypassed by load balancing). The moving-window
strategy avoids the burst-at-boundary problem of fixed windows.

Limits live in `settings` (not hard-coded in decorators) so they are tunable per
environment and overridable in tests. Decorators reference them via callables so
a settings change is picked up per request.
"""
from slowapi import Limiter
from starlette.requests import Request

from app.core.config import settings


def client_ip(request: Request) -> str:
    """Rate-limit key: the real client IP.

    Behind a trusted reverse proxy (Phase 3 Nginx) the socket peer is the proxy,
    so the true client is the left-most entry of X-Forwarded-For. We only trust
    that header when `trust_proxy` is enabled, otherwise a client could spoof
    XFF to dodge or poison another IP's bucket.
    """
    if settings.trust_proxy:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


limiter = Limiter(
    key_func=client_ip,
    storage_uri=settings.redis_url,
    strategy="moving-window",
    # Don't 500 the request if Redis is unreachable on the *create* path — a
    # rate limiter outage should not take down the API. (The redirect path has
    # its own fail-closed policy for the cache; see ADR-003.)
    swallow_errors=True,
    headers_enabled=True,
)


# Referenced as callables so tests can monkeypatch the values at runtime.
def shorten_limit() -> str:
    return settings.rate_limit_shorten


def redirect_limit() -> str:
    return settings.rate_limit_redirect
