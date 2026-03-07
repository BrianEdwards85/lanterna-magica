# Stage 1: Build frontend assets
FROM node:22-slim AS frontend

RUN apt-get update && apt-get install -y --no-install-recommends \
    default-jdk-headless \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app/web

COPY web/package.json web/package-lock.json ./
RUN npm ci

COPY web/shadow-cljs.edn web/postcss.config.mjs ./
COPY web/src/ src/
COPY web/resources/public/index.html web/resources/public/favicon.svg resources/public/

RUN npm run css:build && npx shadow-cljs release app

# Stage 2: Python runtime
FROM python:3.12-slim AS runtime

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY src/ src/
COPY migrations/ migrations/
COPY settings.toml ./

COPY --from=frontend /app/web/resources/public/ web/resources/public/

RUN useradd --create-home appuser \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

CMD ["uv", "run", "uvicorn", "lanterna_magica.app:app", "--host", "0.0.0.0", "--port", "8000"]
