# syntax=docker/dockerfile:1

# ---- 1. Build the React app -------------------------------------------------
FROM node:22-alpine AS frontend
WORKDIR /build/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
# vite.config.ts writes to ../nexus/static/app
RUN mkdir -p ../nexus/static && npm run build

# ---- 2. Python runtime --------------------------------------------------------
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PORT=8080 \
    PYTHONPATH=/app

WORKDIR /app

# Dependencies first: this layer is cached until pyproject.toml changes. Only the runtime
# dependencies are installed; the app itself runs from /app (PYTHONPATH), not site-packages.
COPY pyproject.toml ./
RUN python -c "import tomllib; print('\n'.join(tomllib.load(open('pyproject.toml','rb'))['project']['dependencies']))" > /tmp/requirements.txt \
    && pip install -r /tmp/requirements.txt \
    && rm /tmp/requirements.txt

COPY alembic.ini ./
COPY migrations ./migrations
COPY nexus ./nexus
COPY --from=frontend /build/nexus/static/app ./nexus/static/app
COPY docker/entrypoint.sh /entrypoint.sh

# Never run as root inside the container.
RUN useradd --create-home --uid 10001 nexus && chmod +x /entrypoint.sh
USER nexus

EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s \
    CMD python -c "import os,urllib.request; urllib.request.urlopen(f'http://127.0.0.1:{os.environ[\"PORT\"]}/healthz')"

ENTRYPOINT ["/entrypoint.sh"]
