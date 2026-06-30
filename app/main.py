from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes import router
from app.core import cache


@asynccontextmanager
async def lifespan(app: FastAPI):
    cache.init_pool()
    yield
    cache.close_pool()


app = FastAPI(title="URL Shortener", version="0.1.0", lifespan=lifespan)
app.include_router(router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
