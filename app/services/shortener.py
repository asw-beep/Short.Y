import re

from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.url import URL
from app.services import base62

ALIAS_PATTERN = re.compile(r"^[a-zA-Z0-9_-]{4,32}$")

# Reserved words — flag for expansion as we add features
RESERVED_WORDS = {
    "api", "admin", "health", "docs", "openapi", "redoc", "static", "shorten",
}


class AliasInvalidError(Exception):
    pass


class AliasReservedError(Exception):
    pass


class AliasTakenError(Exception):
    pass


def _validate_alias(alias: str) -> None:
    if not ALIAS_PATTERN.match(alias):
        raise AliasInvalidError("Alias must be 4-32 chars of [a-zA-Z0-9_-]")
    if alias.lower() in RESERVED_WORDS:
        raise AliasReservedError(f"Alias '{alias}' is reserved")


def create_short_url(db: Session, long_url: str, custom_alias: str | None = None) -> URL:
    if custom_alias is not None:
        _validate_alias(custom_alias)
        url = URL(short_code=custom_alias, long_url=long_url, is_custom=True)
        db.add(url)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            raise AliasTakenError(f"Alias '{custom_alias}' is already taken")
        db.refresh(url)
        return url

    next_id = db.execute(text("SELECT nextval('urls_id_seq')")).scalar_one()
    short_code = base62.encode(next_id)
    url = URL(id=next_id, short_code=short_code, long_url=long_url, is_custom=False)
    db.add(url)
    db.commit()
    db.refresh(url)
    return url


def get_by_code(db: Session, code: str) -> URL | None:
    return db.execute(select(URL).where(URL.short_code == code)).scalar_one_or_none()
