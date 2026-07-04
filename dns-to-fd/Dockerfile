FROM ghcr.io/astral-sh/uv:python3.14-bookworm-slim AS build

ENV UV_PYTHON_DOWNLOADS=0
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

COPY ./src ./src/
COPY ./README.md ./
COPY ./pyproject.toml ./
COPY ./uv.lock ./

RUN uv sync --no-dev --no-editable

FROM python:3.14-slim-bookworm

RUN apt-get update \
      && apt-get install -y --no-install-recommends curl openssl libssl3 nano \
      && rm -rf /var/lib/apt/lists/*

RUN groupadd -r apprunner && useradd -r -g apprunner appuser

RUN mkdir -p /home/appuser && chown -R appuser:apprunner /home/appuser

COPY --from=build --chown=appuser:apprunner /.venv ./.venv

ENV PATH="/.venv/bin:$PATH"

USER appuser

EXPOSE 8000

CMD ["uvicorn", "dns_to_fd.app:app", "--host", "0.0.0.0", "--port", "8000"]
