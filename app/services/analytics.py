"""Click analytics via a Redis Stream + a consumer-group worker (Phase 2).

Design (matches the EDD's V4 "Analytics Worker" box):

    redirect  --XADD-->  clicks:stream  --XREADGROUP-->  worker  --INSERT-->  Postgres

Why a stream and not a synchronous INSERT on the redirect path:
- The redirect is the latency-critical hot path (<100 ms target). Writing to
  Postgres on every hit couples redirect latency to write-path health and burns
  the DB connection pool under read-heavy load.
- A Redis Stream is a durable, append-only log. Producing is one fast `XADD`;
  a separate worker drains it in batches. Consumer groups give at-least-once
  delivery with explicit `XACK`, so a worker crash re-delivers un-acked events
  instead of losing them.

Producing is best-effort: analytics must never break a redirect, so `record_click`
swallows Redis errors (they're logged). Losing a click is acceptable; failing a
redirect is not.
"""
from datetime import datetime, timezone

import redis
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logging import get_logger
from app.models.click import Click

log = get_logger("analytics")

STREAM = "clicks:stream"
GROUP = "analytics"
CONSUMER = "worker-1"

# Redis-side truncation: an approximate cap so an offline worker can't let the
# stream grow without bound. '~' lets Redis trim efficiently at node boundaries.
_MAXLEN = None  # set from settings at call time


def record_click(client: redis.Redis, code: str, referrer: str | None, user_agent: str | None) -> None:
    """Producer — append a click event to the stream. Best-effort; never raises."""
    try:
        client.xadd(
            STREAM,
            {
                "code": code,
                "ts": datetime.now(timezone.utc).isoformat(),
                "referrer": referrer or "",
                "user_agent": (user_agent or "")[:512],
            },
            maxlen=settings.analytics_stream_maxlen,
            approximate=True,
        )
    except redis.RedisError:
        # Analytics is non-critical; a redirect must still succeed.
        log.warning("click_record_failed", code=code)


def ensure_group(client: redis.Redis) -> None:
    """Create the consumer group (and the stream) if absent. Idempotent."""
    try:
        client.xgroup_create(STREAM, GROUP, id="0", mkstream=True)
    except redis.ResponseError as e:
        if "BUSYGROUP" not in str(e):
            raise


def _parse_ts(raw: str) -> datetime:
    try:
        return datetime.fromisoformat(raw)
    except (ValueError, TypeError):
        return datetime.now(timezone.utc)


def process_batch(db: Session, client: redis.Redis, count: int = 100, block_ms: int = 5000) -> int:
    """Consume up to `count` pending events, persist them, and ack.

    Returns the number of events processed. Split out from the run loop so it is
    unit-testable with the same DB/redis fixtures the API tests use.
    """
    ensure_group(client)
    resp = client.xreadgroup(GROUP, CONSUMER, {STREAM: ">"}, count=count, block=block_ms)
    if not resp:
        return 0

    processed_ids: list[str] = []
    rows: list[Click] = []
    for _stream, entries in resp:
        for entry_id, fields in entries:
            rows.append(
                Click(
                    short_code=fields["code"],
                    clicked_at=_parse_ts(fields.get("ts", "")),
                    referrer=fields.get("referrer") or None,
                    user_agent=fields.get("user_agent") or None,
                )
            )
            processed_ids.append(entry_id)

    if rows:
        db.add_all(rows)
        db.commit()
        # Ack only after a durable commit — at-least-once. A crash between commit
        # and ack merely re-delivers, which at worst double-counts a click.
        client.xack(STREAM, GROUP, *processed_ids)
        log.info("clicks_persisted", count=len(rows))

    return len(rows)


def get_stats(db: Session, code: str) -> dict:
    """Aggregate stats for a code from persisted (worker-drained) events."""
    total, last = db.execute(
        select(func.count(Click.id), func.max(Click.clicked_at)).where(Click.short_code == code)
    ).one()
    return {
        "short_code": code,
        "total_clicks": total or 0,
        "last_clicked_at": last.isoformat() if last else None,
    }
