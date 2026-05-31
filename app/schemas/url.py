from pydantic import BaseModel, Field, HttpUrl, field_validator


class ShortenRequest(BaseModel):
    url: HttpUrl
    custom_alias: str | None = Field(default=None, min_length=4, max_length=32)

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


class ShortenResponse(BaseModel):
    short_url: str
    short_code: str
    long_url: str
