from datetime import datetime, timezone

from pydantic import BaseModel, Field, HttpUrl, field_validator


class ShortenRequest(BaseModel):
    url: HttpUrl
    custom_alias: str | None = Field(default=None, min_length=4, max_length=32)
    # Optional expiry (ISO 8601). Omit for a link that never expires.
    expires_at: datetime | None = None

    @field_validator("url")
    @classmethod
    def only_http_schemes(cls, v: HttpUrl) -> HttpUrl:
        if v.scheme not in {"http", "https"}:
            raise ValueError("Only http and https URLs are allowed")
        return v

    @field_validator("url")
    @classmethod
    def url_length_cap(cls, v: HttpUrl) -> HttpUrl:
        if len(str(v)) > 2048:
            raise ValueError("URL exceeds 2048 character limit")
        return v

    @field_validator("expires_at")
    @classmethod
    def expiry_must_be_future(cls, v: datetime | None) -> datetime | None:
        if v is None:
            return v
        # Treat a naive datetime as UTC so comparison is unambiguous.
        if v.tzinfo is None:
            v = v.replace(tzinfo=timezone.utc)
        if v <= datetime.now(timezone.utc):
            raise ValueError("expires_at must be in the future")
        return v


class ShortenResponse(BaseModel):
    short_url: str
    short_code: str
    long_url: str
    expires_at: datetime | None = None


class StatsResponse(BaseModel):
    short_code: str
    total_clicks: int
    last_clicked_at: str | None


class URLListItem(BaseModel):
    short_code: str
    short_url: str
    long_url: str
    expires_at: datetime | None
    created_at: datetime


class URLListResponse(BaseModel):
    items: list[URLListItem]
    limit: int
    offset: int
