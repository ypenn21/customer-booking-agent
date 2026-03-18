# ── Stage 1: Build dependencies ────────────────────────────────────────────────
# Use slim for smaller base; install build tools only in this stage
FROM python:3.12-slim AS builder

WORKDIR /build

# Install build essentials (needed for some native C extensions in vertexai deps)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create an isolated virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install Python dependencies (layer-cached; only rebuilds on requirements.txt change)
COPY requirements.txt .
RUN pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

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
# Cloud Run injects PORT at runtime (default 8080).
# PYTHONUNBUFFERED ensures logs stream in real time to Cloud Logging.
ENV PORT=8080 \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

EXPOSE 8080

# ── Entrypoint ─────────────────────────────────────────────────────────────────
# One uvicorn worker per container — Cloud Run scales horizontally via instances.
# Module path: fast-api-fe.main:app  (resolved relative to WORKDIR /app)
CMD ["sh", "-c", "uvicorn fast-api-fe.main:app --host 0.0.0.0 --port $PORT --workers 1 --log-level info"]
