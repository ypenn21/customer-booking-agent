# ── Stage 1: Build dependencies ────────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /build

# Install uv and build essentials
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install frozen dependencies from requirements.txt (generated from uv.lock)
# into a virtual environment for the runtime stage
COPY requirements.txt .
RUN uv venv /opt/venv && \
    . /opt/venv/bin/activate && \
    uv pip install -r requirements.txt

# ── Stage 2: Runtime image ──────────────────────────────────────────────────────
# Start fresh from slim — no build tools, no pip, smaller attack surface
FROM python:3.12-slim AS runtime

WORKDIR /app

# Copy only the virtual env from the builder stage
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy application source into /app/fast-api-fe so the module path resolves
COPY . /app/fast-api-fe

# ── Security: run as non-root user ──────────────────────────────────────────────
RUN groupadd --system appgroup \
    && useradd --system --gid appgroup --no-create-home appuser
USER appuser

# ── Cloud Run configuration ─────────────────────────────────────────────────────
ENV PORT=8080 \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

EXPOSE 8080

# ── Entrypoint ─────────────────────────────────────────────────────────────────
CMD ["sh", "-c", "uvicorn fast-api-fe.main:app --host 0.0.0.0 --port $PORT --workers 1 --log-level info"]
