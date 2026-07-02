"""Analytics tests (Phase 2): stream producer + worker drain + stats endpoint.

These exercise the full path with the same DB/Redis fixtures the API uses: a
redirect XADDs an event, the worker's `process_batch` drains it into Postgres,
and `GET /stats/{code}` reflects it.
"""
import asyncio

import redis

from app.services import analytics


def test_redirect_enqueues_and_worker_persists(client, db_session, cache_client):
    client.post("/shorten", json={"url": "https://example.com/dest"})

    # Two redirects → two events on the stream.
    assert client.get("/0000001", follow_redirects=False).status_code == 301
    assert client.get("/0000001", follow_redirects=False).status_code == 301
    assert cache_client.xlen(analytics.STREAM) == 2

    # Worker drains them into Postgres.
    processed = analytics.process_batch(db_session, cache_client, block_ms=200)
    assert processed == 2

    # Stats now reflect the persisted clicks.
    r = client.get("/stats/0000001")
    assert r.status_code == 200
    body = r.json()
    assert body["short_code"] == "0000001"
    assert body["total_clicks"] == 2
    assert body["last_clicked_at"] is not None


def test_stats_zero_for_unknown_code(client):
    r = client.get("/stats/neverclicked")
    assert r.status_code == 200
    assert r.json()["total_clicks"] == 0
    assert r.json()["last_clicked_at"] is None


def test_processed_events_are_acked_not_redelivered(client, db_session, cache_client):
    client.post("/shorten", json={"url": "https://example.com/x"})
    client.get("/0000001", follow_redirects=False)

    assert analytics.process_batch(db_session, cache_client, block_ms=200) == 1
    # Second drain sees nothing new — the first batch was XACK'd.
    assert analytics.process_batch(db_session, cache_client, block_ms=200) == 0


def test_click_metadata_is_captured(client, db_session, cache_client):
    client.post("/shorten", json={"url": "https://example.com/dest"})
    client.get(
        "/0000001",
        follow_redirects=False,
        headers={"User-Agent": "pytest-UA/1.0", "Referer": "https://ref.example/"},
    )
    analytics.process_batch(db_session, cache_client, block_ms=200)

    from app.models.click import Click

    row = db_session.query(Click).filter(Click.short_code == "0000001").one()
    assert row.user_agent == "pytest-UA/1.0"
    assert row.referrer == "https://ref.example/"


def test_inprocess_worker_drains_clicks(client, db_session, cache_client):
    """ADR-013: the Render-free-tier fallback that drains the stream inside the
    web process via asyncio, instead of a separate worker process.

    Sequencing note: shorten+redirect run synchronously first (before the worker
    task exists), and `asyncio.run(...)` below blocks until the task is fully
    stopped before returning — so there's no concurrent access to the shared
    `db_session` from two threads at once, despite it being reused across both
    the request-handling path and the worker loop.
    """
    client.post("/shorten", json={"url": "https://example.com/inproc"})
    client.get("/0000001", follow_redirects=False)
    assert cache_client.xlen(analytics.STREAM) == 1

    stop_event = asyncio.Event()

    async def run_briefly():
        task = asyncio.create_task(
            analytics.run_inprocess_worker(
                cache_client, lambda: db_session, stop_event, poll_interval=0.2
            )
        )
        await asyncio.sleep(0.6)
        stop_event.set()
        await asyncio.wait_for(task, timeout=2)

    asyncio.run(run_briefly())

    stats = client.get("/stats/0000001").json()
    assert stats["total_clicks"] == 1


def test_inprocess_worker_uses_distinct_consumer_name(cache_client, db_session):
    """The in-process consumer must not collide with the standalone worker's."""
    analytics.record_click(cache_client, code="x", referrer=None, user_agent=None)

    processed = analytics.process_batch(
        db_session, cache_client, block_ms=200, consumer=analytics.INPROCESS_CONSUMER
    )
    assert processed == 1
    assert analytics.INPROCESS_CONSUMER != analytics.CONSUMER


def test_record_click_is_best_effort(cache_client):
    """A Redis failure while recording must not raise into the redirect path."""

    class BrokenRedis:
        def xadd(self, *a, **k):
            raise redis.ConnectionError("down")

    # Should swallow the error, not propagate.
    analytics.record_click(BrokenRedis(), code="x", referrer=None, user_agent=None)
