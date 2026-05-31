import pytest

from app.services import shortener
from app.services.shortener import (
    AliasInvalidError,
    AliasReservedError,
    AliasTakenError,
)


def test_create_auto_short_code(db_session):
    url = shortener.create_short_url(db_session, "https://example.com/")
    assert url.short_code == "0000001"
    assert url.is_custom is False


def test_sequential_codes(db_session):
    a = shortener.create_short_url(db_session, "https://a.com/")
    b = shortener.create_short_url(db_session, "https://b.com/")
    assert a.short_code == "0000001"
    assert b.short_code == "0000002"


def test_custom_alias_success(db_session):
    url = shortener.create_short_url(db_session, "https://example.com/", custom_alias="my-link")
    assert url.short_code == "my-link"
    assert url.is_custom is True


def test_custom_alias_duplicate(db_session):
    shortener.create_short_url(db_session, "https://a.com/", custom_alias="dup1")
    with pytest.raises(AliasTakenError):
        shortener.create_short_url(db_session, "https://b.com/", custom_alias="dup1")


def test_custom_alias_invalid_chars(db_session):
    with pytest.raises(AliasInvalidError):
        shortener.create_short_url(db_session, "https://a.com/", custom_alias="has spaces")


def test_custom_alias_too_short(db_session):
    with pytest.raises(AliasInvalidError):
        shortener.create_short_url(db_session, "https://a.com/", custom_alias="abc")


def test_custom_alias_reserved(db_session):
    with pytest.raises(AliasReservedError):
        shortener.create_short_url(db_session, "https://a.com/", custom_alias="admin")


def test_get_by_code_found(db_session):
    created = shortener.create_short_url(db_session, "https://example.com/")
    fetched = shortener.get_by_code(db_session, created.short_code)
    assert fetched is not None
    assert fetched.long_url == "https://example.com/"


def test_get_by_code_missing(db_session):
    assert shortener.get_by_code(db_session, "nope123") is None
