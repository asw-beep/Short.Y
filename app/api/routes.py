import redis
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.core.cache import get_cache
from app.core.config import settings
from app.core.database import get_db
from app.core.ratelimit import limiter, redirect_limit, shorten_limit
from app.schemas.url import ShortenRequest, ShortenResponse, StatsResponse
from app.services import analytics, shortener
from app.services.shortener import (
    AliasInvalidError,
    AliasReservedError,
    AliasTakenError,
    URLExpiredError,
)

router = APIRouter()

@router.post("/shorten", response_model=ShortenResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit(shorten_limit)
def shorten(
    request: Request,
    response: Response,
    payload: ShortenRequest,
    db: Session = Depends(get_db),
) -> ShortenResponse:
    try:
        url = shortener.create_short_url(
            db,
            long_url=str(payload.url),
            custom_alias=payload.custom_alias,
            expires_at=payload.expires_at,
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
        expires_at=url.expires_at,
    )


@router.get("/stats/{code}", response_model=StatsResponse)
@limiter.limit(redirect_limit)
def stats(
    request: Request,
    response: Response,
    code: str,
    db: Session = Depends(get_db),
) -> StatsResponse:
    """Aggregated click stats. Eventually consistent: reflects events already
    drained from the stream by the analytics worker."""
    return StatsResponse(**analytics.get_stats(db, code))


@router.get("/{code}")
@limiter.limit(redirect_limit)
def redirect(
    request: Request,
    code: str,
    db: Session = Depends(get_db),
    cache: redis.Redis = Depends(get_cache),
) -> RedirectResponse:
    try:
        long_url = shortener.resolve_long_url(db, cache, code)
    except redis.RedisError:
        # Fail-closed: Redis is a hard dependency for redirects (ADR-003).
        raise HTTPException(status_code=503, detail="Cache unavailable")
    except URLExpiredError:
        raise HTTPException(status_code=410, detail="Short link has expired")
    if long_url is None:
        raise HTTPException(status_code=404, detail="Short code not found")

    # Record the click for analytics — best-effort, off the critical path.
    analytics.record_click(
        cache,
        code=code,
        referrer=request.headers.get("referer"),
        user_agent=request.headers.get("user-agent"),
    )
    return RedirectResponse(url=long_url, status_code=301)
