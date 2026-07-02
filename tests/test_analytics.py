"""Analytics tests (Phase 2): stream producer + worker drain + stats endpoint.

These exercise the full path with the same DB/Redis fixtures the API uses: a
redirect XADDs an event, the worker's `process_batch` drains it into Postgres,
and `GET /stats/{code}` reflects it.
"""
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


def test_record_click_is_best_effort(cache_client):
    """A Redis failure while recording must not raise into the redirect path."""

    class BrokenRedis:
        def xadd(self, *a, **k):
            raise redis.ConnectionError("down")

    # Should swallow the error, not propagate.
    analytics.record_click(BrokenRedis(), code="x", referrer=None, user_agent=None)
