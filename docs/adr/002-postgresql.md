# ADR 002 — Use PostgreSQL

**Decision:** Use PostgreSQL as the primary store.

**Alternatives:** MySQL, MongoDB.

**Reason:**
- Strong indexing on `short_code`.
- ACID transactions.
- Atomic UNIQUE constraint prevents alias-collision races at the DB layer.
- Native sequences (`urls_id_seq`) — we use `nextval()` as the source for Base62 encoding.

**Consequences:**
- More schema planning than a document store.
- Sequence becomes a write bottleneck at extreme scale (acceptable for Phase 1).
