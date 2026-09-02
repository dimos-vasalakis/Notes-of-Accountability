FROM python:3.11-slim AS base

WORKDIR /app

COPY pyproject.toml alembic.ini ./
COPY app ./app
COPY migrations ./migrations

# --- dev target: used by docker-compose.yml ---
FROM base AS dev

RUN pip install --no-cache-dir .

COPY docker-entrypoint.dev.sh ./
RUN chmod +x docker-entrypoint.dev.sh

EXPOSE 8000

ENTRYPOINT ["./docker-entrypoint.dev.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# --- prod target: used by docker-compose.prod.yml ---
FROM base AS builder

RUN pip install --no-cache-dir --prefix=/install .

FROM python:3.11-slim AS prod

WORKDIR /app

COPY --from=builder /install /usr/local
COPY --from=builder /app/alembic.ini ./
COPY --from=builder /app/migrations ./migrations
COPY docker-entrypoint.prod.sh ./

RUN groupadd --system app && useradd --system --gid app app \
    && chown -R app:app /app \
    && chmod +x docker-entrypoint.prod.sh
USER app

EXPOSE 8000

ENTRYPOINT ["./docker-entrypoint.prod.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
