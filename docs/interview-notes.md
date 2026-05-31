# Interview Notes

## Why PostgreSQL?
Strong indexing, transactions, atomic UNIQUE constraints (prevents alias-collision races at the DB layer), mature ecosystem. We also use its sequence (`urls_id_seq`) as the source of monotonic IDs for Base62 encoding.

## Why Redis? (Phase 2)
Hot URLs get hit repeatedly. Redis lets us serve redirects without touching Postgres, dropping latency and DB load. Also doubles as a rate-limit counter store.

## Why not MongoDB?
We don't need document flexibility; we need a UNIQUE constraint that's enforced atomically and a fast sequence. Both are first-class in Postgres.

## Why cache redirects?
Read-heavy workload, immutable mappings. Cache-aside on `short_code → long_url` is a near-perfect fit.

## How are collisions prevented?
- Auto-generated codes: derived from a Postgres sequence, so unique by construction.
- Custom aliases: UNIQUE constraint on `short_code`; duplicate inserts raise `IntegrityError` → 409. No application-level race window.

## How would you scale to 10M URLs?
Phase 1 already handles this on a single Postgres node — 10M rows on an indexed `short_code` is small. Add a read replica if read QPS gets high.

## How would you scale to 100k req/sec?
- Redis in front of Postgres (Phase 2).
- Horizontal scale FastAPI behind Nginx (Phase 3).
- Read replicas for Postgres; sharding becomes relevant past ~1B rows.
- The sequence becomes a bottleneck eventually — switch to random codes or sharded ID generation.

## What was the hardest bug?
*(populate as work progresses)*

## What would you improve in V2?
- Switch to random Base62 codes to remove enumeration risk.
- Multi-region deployment with geo-DNS.
- URL safety scanning.
