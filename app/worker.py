"""Analytics worker — a standalone process that drains the click stream into
Postgres. Run alongside the API (its own container in docker-compose).

    python -m app.worker

It loops on `process_batch`, which blocks on Redis until events arrive, so the
loop is not a busy-wait. SIGTERM/SIGINT stop it cleanly between batches.
"""
import signal
import sys

from app.core.cache import get_client
from app.core.database import SessionLocal
from app.core.logging import configure_logging, get_logger
from app.services import analytics

configure_logging()
log = get_logger("worker")

_running = True


def _stop(signum, _frame):
    global _running
    log.info("worker_stopping", signal=signum)
    _running = False


def run() -> None:
    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)

    client = get_client()
    analytics.ensure_group(client)
    log.info("worker_started", stream=analytics.STREAM, group=analytics.GROUP)

    while _running:
        db = SessionLocal()
        try:
            # Blocks up to block_ms for new events, so this is not a busy loop.
            analytics.process_batch(db, client, count=200, block_ms=2000)
        except Exception:
            log.exception("worker_batch_failed")
            db.rollback()
        finally:
            db.close()

    log.info("worker_exited")


if __name__ == "__main__":
    try:
        run()
    except KeyboardInterrupt:
        sys.exit(0)
