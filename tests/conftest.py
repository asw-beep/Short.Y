import os

# Point the app at the isolated test Redis DB (/1) BEFORE importing anything that
# reads settings — the rate limiter binds its storage backend at import time.
# This keeps rate-limit buckets in the same DB that `cache_client` flushes.
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/1")

import pytest
import redis as redis_lib
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.core.cache import get_cache
from app.core.database import Base, get_db
from app.main import app
from app.models import url  # noqa: F401

TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql://shortener:shortener@localhost:5432/shortener_test",
)

# Separate logical DB index (/1) so FLUSHDB never touches dev cache data —
# mirrors the separate `shortener_test` database choice for Postgres.
TEST_REDIS_URL = os.getenv("TEST_REDIS_URL", "redis://localhost:6379/1")

engine = create_engine(TEST_DATABASE_URL)
TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)

test_redis = redis_lib.Redis.from_url(TEST_REDIS_URL, decode_responses=True)


@pytest.fixture(scope="session", autouse=True)
def _setup_db():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)


@pytest.fixture
def db_session():
    session = TestSession()
    try:
        session.execute(text("TRUNCATE TABLE urls RESTART IDENTITY CASCADE"))
        session.commit()
        yield session
    finally:
        session.close()


@pytest.fixture
def cache_client():
    test_redis.flushdb()
    yield test_redis
    test_redis.flushdb()


@pytest.fixture
def client(db_session, cache_client):
    def _override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_cache] = lambda: cache_client
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
