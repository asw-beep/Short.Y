# ADR 009 — Container Hardening

**Status:** Implemented (Phase 3).

**Decision:** Ship a **multi-stage**, **non-root** image with a baked-in
**HEALTHCHECK**, and treat `docker-compose.yml` as a *dev override* of the image's
production default command.

**Changes:**
- **Multi-stage build:** a `builder` stage installs dependencies into `/install`;
  the `runtime` stage copies only that tree — no pip cache, no build toolchain.
  (All deps are wheels — `psycopg2-binary` bundles libpq — so no compiler/apt is
  needed at all.)
- **Non-root:** a system `app` user owns `/code` and runs the process. A container
  breakout now lands as an unprivileged user, not root.
- **HEALTHCHECK:** probes `/livez` (liveness, no dependency I/O) so orchestrators
  see real process health without false negatives from a transient DB blip.
- **Prod-default CMD** is plain `uvicorn` (no `--reload`, no bind mount). Compose
  overrides it for dev (migrations + `--reload`), keeping the image production-safe
  by default.
- **`.dockerignore`** keeps tests/docs/.git/.env out of the build context and image.
- **Secrets/config externalised:** compose reads `${POSTGRES_PASSWORD:-…}` etc.
  from the environment/`.env` with dev defaults, instead of hard-coding a
  production-looking secret in the file.
- **Worker healthcheck disabled** — it shares the image but serves no HTTP, so the
  `/livez` probe would always fail; disabled rather than inherited.

**Alternatives considered:**
- Single-stage image — simpler but ships the toolchain/cache and is fatter.
- Distroless base — smaller/harder, but no shell complicates the compose dev
  command and migration step; slim is a pragmatic middle ground for now.
- Docker/compose *secrets* files — heavier than needed for local dev; env
  externalisation is the incremental step. Real secret management is a deploy-time
  concern (Phase 3+ / platform).

**Consequences:**
- Two build stages to reason about.
- Non-root means writable paths must be owned by `app` (only `/code` today).
- Compose still maps DB/Redis ports to the host for local access — a dev-only
  convenience, not for production exposure (see threat model).
