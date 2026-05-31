# ADR 001 — Use FastAPI

**Decision:** Use FastAPI for the HTTP layer.

**Alternatives:** Flask, Django, Starlette (bare).

**Reason:**
- Async support out of the box.
- Pydantic-based request validation eliminates a class of boilerplate and bugs.
- Auto-generated OpenAPI docs — saves building a frontend in Phase 1.
- Fast iteration.

**Consequences:**
- Tied to Pydantic v2 semantics.
- Async-aware code path (we use sync SQLAlchemy in Phase 1 for simplicity).
