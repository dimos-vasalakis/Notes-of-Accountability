.PHONY: help dev backend frontend install install-backend install-frontend \
	migrate makemigration test lint build up down logs

help:
	@echo "Available targets:"
	@echo "  install            Install backend and frontend dependencies"
	@echo "  backend            Run backend dev server (uvicorn --reload)"
	@echo "  frontend           Run frontend dev server (next dev)"
	@echo "  migrate            Apply alembic migrations"
	@echo "  makemigration m=\"msg\"  Create a new alembic migration"
	@echo "  test               Run backend tests"
	@echo "  lint               Run frontend lint"
	@echo "  build              Build frontend for production"
	@echo "  up                 Start docker-compose stack"
	@echo "  down               Stop docker-compose stack"
	@echo "  logs               Tail docker-compose logs"

install: install-backend install-frontend

install-backend:
	cd backend && uv sync --extra dev

install-frontend:
	cd frontend && npm install

backend:
	cd backend && uv run uvicorn app.main:app --reload

frontend:
	cd frontend && npm run dev

migrate:
	cd backend && uv run alembic upgrade head

makemigration:
	cd backend && uv run alembic revision --autogenerate -m "$(m)"

test:
	cd backend && uv run pytest

lint:
	cd frontend && npm run lint

build:
	cd frontend && npm run build

up:
	docker compose up -d

down:
	docker compose down

logs:
	docker compose logs -f
