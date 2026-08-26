# Note of Accountability (NoA)

A productivity & accountability system for high-performance students and engineers. NoA unifies markdown notes, task tracking, and automated due-task push notifications in one app.

## Tech Stack

- **Backend:** Python 3.11, FastAPI, SQLModel (async, on SQLAlchemy 2.0 core), Alembic, Pydantic v2
- **Frontend:** TypeScript, Next.js (App Router)
- **Database:** PostgreSQL 15
- **Architecture:** Layered — API routers → services → models/schemas

## Project Structure

```
backend/
  app/
    api/routers/     # FastAPI endpoints (auth, notes, tasks, push_subscriptions)
    services/         # Business logic
    models/           # SQLModel ORM models
    schemas/          # Pydantic request/response schemas
    core/             # Config, db session, security, exceptions
  migrations/         # Alembic migrations
  tests/

frontend/
  app/                # Next.js App Router pages, layouts, and components
    sw.js/route.ts    # Service worker, served at /sw.js (kept as .ts, not public/sw.js)
  lib/                # API client, hooks, shared types
  components/         # Shared UI components

nginx/                # Reverse proxy config for production
```

## Getting Started

### Prerequisites

- Docker and Docker Compose
- (For local, non-Docker dev) Python 3.11+ and Node.js 20+

### Environment Setup

Copy the example env files and fill in real values:

```bash
cp .env.example .env
cp backend/.env.example backend/.env
cp frontend/.env.local.example frontend/.env.local
```

Notable variables:

| File | Variable | Purpose |
| --- | --- | --- |
| `backend/.env` | `DATABASE_URL` | Async Postgres connection string |
| `backend/.env` | `SECRET_KEY` | JWT signing secret — change from the default |
| `backend/.env` | `VAPID_PUBLIC_KEY` / `VAPID_PRIVATE_KEY` / `VAPID_SUBJECT` | Web push credentials for task-due notifications |
| `frontend/.env.local` | `NEXT_PUBLIC_API_URL` | Backend base URL |
| `frontend/.env.local` | `NEXT_PUBLIC_VAPID_PUBLIC_KEY` | Must match `backend/.env`'s `VAPID_PUBLIC_KEY` |

Generate a VAPID key pair with:

```bash
npx web-push generate-vapid-keys
```

### Run with Docker Compose

```bash
docker compose up
```

This starts Postgres, the backend (`localhost:8000`), and the frontend (`localhost:3000`) with hot reload.

### Run Backend Locally

```bash
cd backend
uvicorn app.main:app --reload
```

### Run Frontend Locally

```bash
cd frontend
npm install
npm run dev
```

## Database Migrations

```bash
cd backend
alembic upgrade head                              # apply migrations
alembic revision --autogenerate -m "description"  # create a new migration
```

## Testing

```bash
cd backend
pytest
```

## Production

`docker-compose.prod.yml` builds production images for the backend and frontend behind the Nginx reverse proxy config in `nginx/`.
