import time
from contextlib import asynccontextmanager
from pathlib import Path
from uuid import uuid4

import redis
import structlog
from fastapi import Depends, FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi.errors import RateLimitExceeded
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.routes import router
from app.core import cache
from app.core.cache import get_cache
from app.core.database import get_db
from app.core.logging import configure_logging, get_logger
from app.core.ratelimit import client_ip, limiter
from app.core.ratelimit_handler import rate_limit_exceeded_handler

configure_logging()
log = get_logger("app")

WEB_DIR = Path(__file__).parent / "web"


@asynccontextmanager
async def lifespan(app: FastAPI):
    cache.init_pool()
    log.info("startup_complete")
    yield
    cache.close_pool()


app = FastAPI(title="URL Shortener", version="0.1.0", lifespan=lifespan)

# Rate limiting: attach the limiter to app state and register the 429 handler.
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)


@app.middleware("http")
async def request_logging(request: Request, call_next):
    """Bind a request_id + request context, log completion, echo X-Request-ID."""
    request_id = request.headers.get("x-request-id") or uuid4().hex
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(
        request_id=request_id,
        method=request.method,
        path=request.url.path,
        client_ip=client_ip(request),
    )
    start = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        log.exception("request_failed")
        raise
    duration_ms = round((time.perf_counter() - start) * 1000, 2)
    log.info("request_completed", status_code=response.status_code, duration_ms=duration_ms)
    response.headers["X-Request-ID"] = request_id
    return response


@app.get("/livez", tags=["health"])
def liveness() -> dict[str, str]:
    """Liveness: the process is up. No dependency checks (used by container HC)."""
    return {"status": "ok"}


@app.get("/health", tags=["health"])
def readiness(
    db: Session = Depends(get_db),
    cache_client: redis.Redis = Depends(get_cache),
) -> JSONResponse:
    """Readiness: verifies the app can actually serve — DB and Redis reachable.

    Returns 503 (not 200) if any dependency is down, so load balancers stop
    routing traffic to a degraded instance.
    """
    checks: dict[str, str] = {}
    healthy = True

    try:
        db.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception:
        checks["database"] = "down"
        healthy = False

    try:
        cache_client.ping()
        checks["redis"] = "ok"
    except Exception:
        checks["redis"] = "down"
        healthy = False

    if not healthy:
        log.warning("readiness_degraded", checks=checks)

    return JSONResponse(
        status_code=200 if healthy else 503,
        content={"status": "ok" if healthy else "degraded", "checks": checks},
    )


# Frontend (plain HTML/CSS/JS, no build step). /static is CSS/JS assets; the two
# pages are served directly. Registered — like /livez, /health — before the
# catch-all GET /{code}, so "list" is also in RESERVED_WORDS (shortener.py).
app.mount("/static", StaticFiles(directory=WEB_DIR / "static"), name="static")


@app.get("/", include_in_schema=False)
def index_page() -> FileResponse:
    return FileResponse(WEB_DIR / "index.html")


@app.get("/list", include_in_schema=False)
def list_page() -> FileResponse:
    return FileResponse(WEB_DIR / "list.html")


# Registered last: the router owns the catch-all GET /{code}, which must not
# shadow fixed system routes (/livez, /health, /shorten, /, /list). Route
# matching is registration-order, so fixed paths are declared before the catch-all.
app.include_router(router)
