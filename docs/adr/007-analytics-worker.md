# ADR 007 — Click Analytics via Redis Streams + Worker

**Status:** Implemented (Phase 2).

**Decision:** Record a click by `XADD`-ing an event to a **Redis Stream** on the
redirect path; a **separate worker process** consumes the stream with a
**consumer group** and batch-inserts rows into a Postgres `clicks` table.
`GET /stats/{code}` aggregates from that table.

**Alternatives considered:**
- **Synchronous INSERT on redirect** — simplest, but couples redirect latency to
  the write path and burns a DB connection per hit under read-heavy load.
  Rejected: redirect is the <100 ms hot path.
- **FastAPI `BackgroundTasks`** — runs in the same process; no durability, no
  backpressure, lost on crash, and still competes for the API's resources.
- **Redis List (`LPUSH`/`BRPOP`)** — works, but no consumer groups, so no
  at-least-once redelivery or multi-consumer fan-out.
- **Celery / ARQ** — full task queues; more machinery than a single append-only
  event stream needs here. Redis is already a dependency.

**Reason:**
- **Streams** are a durable, append-only log with **consumer groups**: explicit
  `XACK` gives at-least-once delivery, and a crashed worker's un-acked events are
  redelivered instead of lost.
- **Producing is one `XADD`** — negligible added latency on redirect, and it is
  **best-effort**: `record_click` swallows Redis errors so analytics can never
  break a redirect.
- **Batch drain** amortises DB writes; the worker blocks on Redis (`block`), so
  it is not a busy-wait.
- **Bounded memory:** `XADD ... maxlen ~100000` caps the stream so an offline
  worker cannot grow Redis without bound.

**Consistency:** `GET /stats/{code}` is **eventually consistent** — it reflects
events already drained by the worker, not those still in the stream. Acceptable
for click analytics; a redirect is never blocked to keep a counter exact.

**Ordering — ack after commit:** the worker commits the batch to Postgres *before*
`XACK`. A crash in that window re-delivers, which at worst double-counts a click —
chosen over acking first (which could silently drop clicks on a crash).

**Consequences:**
- Stats lag the stream by up to one batch/poll interval.
- One extra Redis op per redirect (the `XADD`).
- A new operational component (the worker container) to run and monitor.
