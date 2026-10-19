# Note of Accountability (NoA)

A productivity and accountability app for students and engineers. NoA combines markdown notes, task tracking, a focus timer, accountability pods, and optional Panhellenic exam-prep tooling, with web push reminders and a server-side streak.

The web app is installable as a PWA (`standalone` manifest, service worker at `/sw.js`).

## Features

- **Notes** — markdown notes owned by the signed-in user (create, edit, list, delete)
- **Tasks** — todo / in progress / done, due dates, and lead-time reminders
- **Focus timer** — Pomodoro-style sessions; completed sessions are stored as study time and can be tagged with an exam subject
- **Accountability pods** — small invite-code groups. Members see each other's display name, daily streak, and recent activity. After 24h of silence the pod gets a push nudge (with a 24h cooldown so one quiet member does not spam the group)
- **Student mode** — opt in at signup for Panhellenic (πανελλήνιες) tooling: exam countdown and a subject-weighted view of whether study hours match what each subject is worth
- **Web push** — due-task and reminder notifications, plus pod inactivity nudges (VAPID + service worker)
- **Auth** — email/password, httpOnly access + refresh cookies, refresh rotation, logout / logout-all, login cooldown after too many failures
- **Theme** — dark by default, with a bright theme persisted in `localStorage`

### Streaks

A day counts toward your streak if you completed at least one task **or** logged at least one study session that day (UTC). Days are computed server-side from `tasks.completed_at` and `study_sessions.occurred_at`, so a streak is consistent across devices and visible to your pod. Not having logged anything *yet today* does not break a streak — it only breaks after a full UTC day with no activity.

## Tech stack

| Layer | Stack |
| --- | --- |
| Backend | Python 3.11, FastAPI, SQLModel (async, SQLAlchemy 2.0), Alembic, Pydantic v2, APScheduler |
| Frontend | TypeScript, Next.js 15 (App Router), React 18, Tailwind CSS 4 |
| Database | PostgreSQL 15 (local Compose) or [Supabase](https://supabase.com) Postgres |
| Cache | Optional Redis (Upstash TCP / `rediss://`). If `REDIS_URL` is unset or Redis is down, the API hits Postgres instead |
| Push | Web Push (VAPID, `pywebpush`) |
| Architecture | Layered — routers → services → models/schemas |

## Project structure

```
backend/
  app/
    api/routers/     # FastAPI endpoints (auth, notes, tasks, pods,
                     #   exam_prep, push_subscriptions)
    services/        # Business logic, including scheduled push jobs
    models/          # SQLModel ORM models
    schemas/         # Pydantic request/response schemas
    core/            # Config, db, cache, security, middleware, exceptions
  migrations/        # Alembic migrations
  scripts/           # Operational scripts (exam subject/date seeding)
  tests/

frontend/
  app/               # Next.js App Router pages, layouts, PWA manifest
    sw.js/route.ts   # Service worker, served at /sw.js (kept as .ts, not public/sw.js)
  components/        # Shared UI
  lib/               # API client, auth context, hooks, types

.github/workflows/   # CI (tests, migrations, frontend typecheck+build) and CD
```

App routes: `/` (landing or home), `/login`, `/signup`, `/notes`, `/tasks`, `/timer`, `/pods`, `/exam-prep`. Backend health: `GET /health`.

## Getting started

### Prerequisites

- Docker and Docker Compose, **or** Python 3.11+, [uv](https://docs.astral.sh/uv/), Node.js 20+, and a Postgres 15 instance
- Optional: a Redis URL (e.g. Upstash) for caching notes, tasks, study sessions, exam reference data, and streaks

### Environment

```bash
cp .env.example .env
cp backend/.env.example backend/.env
cp frontend/.env.local.example frontend/.env.local
```

| File | Variable | Purpose |
| --- | --- | --- |
| `.env` | `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DB` | Compose Postgres credentials |
| `backend/.env` | `DATABASE_URL` | Async Postgres URL. Host Postgres from Compose is mapped to **localhost:5433** |
| `backend/.env` | `MIGRATION_DATABASE_URL` | Optional. Supabase session/direct URL (port 5432) used by Alembic; falls back to `DATABASE_URL` |
| `backend/.env` | `SECRET_KEY` | JWT signing secret — change the default |
| `backend/.env` | `VAPID_PUBLIC_KEY` / `VAPID_PRIVATE_KEY` / `VAPID_SUBJECT` | Web push. Jobs no-op if keys are empty |
| `backend/.env` | `REDIS_URL` | Optional. TCP endpoint (`rediss://…`), not the REST URL |
| `backend/.env` | `CACHE_TTL_SECONDS` | Cache TTL (default 300) |
| `frontend/.env.local` | `NEXT_PUBLIC_API_URL` | Backend base URL (`http://localhost:8000` locally) |
| `frontend/.env.local` | `NEXT_PUBLIC_VAPID_PUBLIC_KEY` | Must match `backend/.env`'s `VAPID_PUBLIC_KEY` |

Generate a VAPID key pair:

```bash
npx web-push generate-vapid-keys
```

### Using Supabase

Copy the connection string from Supabase (Project Settings > Database), switch the scheme to `postgresql+asyncpg://`, and append `?ssl=require`:

- `DATABASE_URL`: transaction pooler, port **6543** (prepared statements are disabled automatically for it)
- `MIGRATION_DATABASE_URL`: session pooler or direct connection, port **5432** (used by `alembic`)

Use a separate Supabase project (or schema) for `TEST_DATABASE_URL`; tests create and drop tables. With Compose, remove the `DATABASE_URL` override on the `backend` service so it uses `backend/.env`.

### Run with Docker Compose

```bash
make up          # or: docker compose up -d
make logs        # tail logs
make down
```

This starts Postgres (host port **5433**), the backend (`localhost:8000`, migrations on container start), and the frontend (`localhost:3000`) with hot reload.

### Run locally (without Compose)

Install deps, point `DATABASE_URL` at your Postgres, then:

```bash
make install     # uv sync --extra dev + npm install
make migrate
make backend     # uv run uvicorn app.main:app --reload
make frontend    # next dev
```

Equivalent without Make:

```bash
cd backend && uv sync --extra dev && uv run alembic upgrade head
uv run uvicorn app.main:app --reload

cd frontend && npm install && npm run dev
```

## Makefile

| Target | What it does |
| --- | --- |
| `make install` | Backend (`uv sync --extra dev`) and frontend (`npm install`) |
| `make backend` / `make frontend` | Dev servers |
| `make migrate` | `alembic upgrade head` |
| `make makemigration m="msg"` | Autogenerate a migration |
| `make test` | Backend pytest |
| `make seed-exam` | Upsert exam subjects, weights, and exam date |
| `make typecheck` / `make build` | Frontend `tsc --noEmit` / production build |
| `make up` / `make down` / `make logs` | Compose stack |

## Database migrations

```bash
make migrate
make makemigration m="description"
```

Or from `backend/`:

```bash
uv run alembic upgrade head
uv run alembic revision --autogenerate -m "description"
```

## Exam configuration (student mode)

> **The seeded exam date and subject weight coefficients are placeholders and are not verified.**
> Panhellenic coefficients and exam dates are set each year by ministry decision (ΦΕΚ) and differ
> between years and between scientific fields (επιστημονικά πεδία). Verify them against the current
> year's official decision before students plan around them.

Subjects, weight coefficients, and the exam date live in the database (`exam_subjects` / `exam_configs`) rather than in code. Initial rows are seeded by the `c1a7d3f90b21` migration.

To edit them, change the constants at the top of `backend/scripts/seed_exam_config.py` and run:

```bash
make seed-exam
# or: cd backend && uv run python -m scripts.seed_exam_config
```

The script upserts by subject `code` and track, so it is safe to run repeatedly. A subject removed from the list is deactivated rather than deleted, keeping historical study sessions readable.

Only the Group D track (Οικονομίας & Πληροφορικής) is seeded today: Νεοελληνική Γλώσσα και Λογοτεχνία, Μαθηματικά, ΑΕΠΠ, and Αρχές Οικονομικής Θεωρίας.

## Testing

```bash
make test
# or: cd backend && uv run pytest
```

Tests build their schema from model metadata, so they do not exercise the migration files. CI covers that separately: `alembic upgrade head`, then `alembic check` (models still match migrations), then a full `downgrade base` / `upgrade head` round trip.

```bash
cd backend
uv run alembic upgrade head && uv run alembic check
```

## CI and CD

`.github/workflows/ci.yml` runs on push and pull request to `main` (and `workflow_dispatch`):

1. Backend tests against Postgres 15
2. Migration apply / `alembic check` / reversible round trip
3. Frontend typecheck + production build

`.github/workflows/cd.yml` runs on push to `main` (and `workflow_dispatch`). It builds the Docker `prod` targets for backend and frontend and pushes:

`{REGISTRY}/{github.repository_owner}/noa-{backend|frontend}:{sha|latest}`

Set repo secrets `REGISTRY`, `REGISTRY_USERNAME`, and `REGISTRY_PASSWORD`. For GHCR, `REGISTRY` should include the registry host used at login (e.g. `ghcr.io`); the image path also includes the repository owner.

There is no `docker-compose.prod.yml` or `nginx/` config in this repo. Production images are multi-stage (`dev` / `prod` targets in each Dockerfile). The frontend production image uses Next.js `output: "standalone"`.

> ESLint is not configured (no config file and no `eslint` dependency), so `npm run lint` / `make lint` drops into an interactive Next.js setup prompt and cannot pass in CI. CI runs `npm run typecheck` instead.

## License

MIT. See [LICENSE](LICENSE).
