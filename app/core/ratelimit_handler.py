"""429 handler for rate-limited requests.

Kept separate from `ratelimit.py` to avoid a circular import (the handler needs
the app/limiter state at request time, not at limiter-construction time). Returns
a consistent JSON body and preserves SlowAPI's standard rate-limit headers
(Retry-After, X-RateLimit-*), which clients use to back off.
"""
from fastapi import Request
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded


def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    response = JSONResponse(
        status_code=429,
        content={"detail": f"Rate limit exceeded: {exc.detail}"},
    )
    # Re-attach Retry-After / X-RateLimit-* headers computed by the limiter.
    limiter = request.app.state.limiter
    return limiter._inject_headers(response, request.state.view_rate_limit)
