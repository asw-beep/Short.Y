from contextlib import asynccontextmanager

from fastapi import FastAPI
from slowapi.errors import RateLimitExceeded

from app.api.routes import router
from app.core import cache
from app.core.ratelimit import limiter
from app.core.ratelimit_handler import rate_limit_exceeded_handler


@asynccontextmanager
async def lifespan(app: FastAPI):
    cache.init_pool()
    yield
    cache.close_pool()


app = FastAPI(title="URL Shortener", version="0.1.0", lifespan=lifespan)

# Rate limiting: attach the limiter to app state and register the 429 handler.
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

app.include_router(router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
