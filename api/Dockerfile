# Local run only (docker compose up, which sets AUTH_MODE=mock). Without AUTH_MODE the API expects
# Cognito and refuses every request. The AWS deploy packages the same code for Lambda instead.
FROM ghcr.io/astral-sh/uv:0.11.32-python3.12-trixie-slim@sha256:519357e414a4240af8b3ac657466c20f9d6041b5a3ce999d96fa9d576ef7fd29
ENV UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never PYTHONDONTWRITEBYTECODE=1
WORKDIR /app/api
COPY api/pyproject.toml api/uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY api/src ./src
RUN uv sync --frozen --no-dev
COPY kg /app/kg
COPY fixtures /app/fixtures
# data/ is not in the image: compose mounts the copy `make data` fetched.
RUN useradd --create-home app && mkdir -p /app/.cache && chown app /app/.cache
USER app
EXPOSE 8000
CMD ["/app/api/.venv/bin/uvicorn", "coachkg.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log", "--no-server-header"]
