FROM python:3.12-slim AS base

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY src/ src/
COPY migrations/ migrations/
COPY settings.toml ./

RUN groupadd --system appuser && useradd --system --gid appuser appuser
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"]

CMD ["uv", "run", "uvicorn", "lanterna_magica.app:app", "--host", "0.0.0.0", "--port", "8000"]
