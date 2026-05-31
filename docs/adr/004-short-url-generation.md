# ADR 004 — Short URL Generation

**Decision:** Auto-generated codes are Base62 of a Postgres sequence value, left-padded to 7 chars.

**Alternatives:**
- Random 7-char Base62 (with collision retry).
- UUID4 truncated.
- Hash-based (e.g. SHA256 of URL, truncated).

**Reason:**
- Simple — no retry/collision logic; the sequence guarantees uniqueness.
- 7 chars over 62 symbols = ~3.5T combinations, plenty of headroom.
- Cheap: one `nextval()` + one INSERT, both in the same transaction.

**Consequences:**
- Codes are sequential and therefore enumerable. Documented in `threat-model.md`. Mitigated by rate limiting (Phase 2).
- Hash-based dedup of identical long URLs would require a separate index — not implemented; we always mint a new code.

**Reserved alias list:** flagged for expansion as new system routes are added (currently `api`, `admin`, `health`, `docs`, `openapi`, `redoc`, `static`, `shorten`).
