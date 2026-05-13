# SecureLedger production image.
# Multi-stage: build frontend with node, run backend with python.
# The backend's FastAPI app serves the compiled frontend as static files,
# so this whole thing ships as ONE container at one URL — no CORS, no
# separate frontend service to manage.

# ---------- Stage 1: build the frontend ----------
FROM node:20-alpine AS frontend-builder

WORKDIR /build

# Install pnpm via corepack so the lockfile in the repo is honored
RUN corepack enable && corepack prepare pnpm@9.12.2 --activate

# Copy manifest first so the install layer caches across code changes
COPY frontend/package.json frontend/pnpm-lock.yaml* ./
RUN pnpm install --frozen-lockfile || pnpm install

# Copy the rest of the frontend and build
COPY frontend/ ./
# Empty VITE_API_BASE_URL = same-origin requests at runtime
ENV VITE_API_BASE_URL=""
RUN pnpm build

# ---------- Stage 2: backend runtime ----------
FROM python:3.12-slim AS runtime

# Common runtime essentials
RUN apt-get update \
 && apt-get install -y --no-install-recommends curl \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps (production only — no [dev] extras)
COPY backend/pyproject.toml ./
RUN pip install --no-cache-dir uv \
 && uv pip install --system --no-cache .

# Copy backend source
COPY backend/app ./app
COPY backend/alembic ./alembic
COPY backend/alembic.ini ./alembic.ini

# Copy the built frontend into /app/static — main.py mounts this on import
COPY --from=frontend-builder /build/dist ./static

# Run as non-root for defense in depth
RUN useradd --create-home --shell /usr/sbin/nologin appuser \
 && chown -R appuser:appuser /app
USER appuser

# Apply migrations on boot, then start gunicorn (production ASGI server,
# uvicorn workers handle async). Single process per VM is fine for Fly's
# free tier; bump --workers when scaling.
ENV PORT=8080
EXPOSE 8080

CMD ["sh", "-c", "alembic upgrade head && gunicorn app.main:app -k uvicorn.workers.UvicornWorker -w 2 -b 0.0.0.0:${PORT} --access-logfile - --error-logfile -"]
