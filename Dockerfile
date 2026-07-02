# syntax=docker/dockerfile:1

# ---- Builder: install dependencies into an isolated prefix ----
FROM python:3.12-slim AS builder

WORKDIR /build
COPY requirements.txt .
# All deps ship as wheels (psycopg2-binary bundles libpq), so no compiler/apt
# packages are needed — keeps the build fast and the final image lean.
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


# ---- Runtime: slim image, non-root, only what's needed to run ----
FROM python:3.12-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Copy the installed dependency tree from the builder (no pip cache, no toolchain).
COPY --from=builder /install /usr/local

WORKDIR /code
COPY app ./app
COPY alembic ./alembic
COPY alembic.ini .

# Run as an unprivileged user, not root.
RUN groupadd --system app && useradd --system --gid app --home-dir /code app \
    && chown -R app:app /code
USER app

EXPOSE 8000

# Liveness probe baked into the image — hits /livez (no dependency I/O).
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request,sys; \
sys.exit(0 if urllib.request.urlopen('http://localhost:8000/livez', timeout=2).status==200 else 1)"

# Production default: no --reload, no bind mount. docker-compose overrides this
# command for local dev.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
