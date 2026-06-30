import redis
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.core.cache import get_cache
from app.core.config import settings
from app.core.database import get_db
from app.schemas.url import ShortenRequest, ShortenResponse
from app.services import shortener
from app.services.shortener import (
    AliasInvalidError,
    AliasReservedError,
    AliasTakenError,
)

router = APIRouter()

@router.get("/health")
def health() -> dict:
    return {"status": "ok"}

@router.post("/shorten", response_model=ShortenResponse, status_code=status.HTTP_201_CREATED)
def shorten(payload: ShortenRequest, db: Session = Depends(get_db)) -> ShortenResponse:
    try:
        url = shortener.create_short_url(
            db,
            long_url=str(payload.url),
            custom_alias=payload.custom_alias,
        )
    except AliasInvalidError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except AliasReservedError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except AliasTakenError as e:
        raise HTTPException(status_code=409, detail=str(e))

    return ShortenResponse(
        short_url=f"{settings.base_url.rstrip('/')}/{url.short_code}",
        short_code=url.short_code,
        long_url=url.long_url,
    )


@router.get("/{code}")
def redirect(
    code: str,
    db: Session = Depends(get_db),
    cache: redis.Redis = Depends(get_cache),
) -> RedirectResponse:
    try:
        long_url = shortener.resolve_long_url(db, cache, code)
    except redis.RedisError:
        # Fail-closed: Redis is a hard dependency for redirects (ADR-003).
        raise HTTPException(status_code=503, detail="Cache unavailable")
    if long_url is None:
        raise HTTPException(status_code=404, detail="Short code not found")
    return RedirectResponse(url=long_url, status_code=301)
