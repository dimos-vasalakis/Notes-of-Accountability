# Note of Accountability (NoA)

A productivity & accountability system for high-performance students and engineers. NoA unifies markdown notes, task tracking, focus timers, and automated push notifications in one app.

## Features

- **Notes & tasks** — markdown notes, task tracking with due dates and lead-time reminders
- **Focus timer** — Pomodoro-style sessions, optionally tagged with a study subject
- **Accountability pods** — small invite-code groups; everyone sees each member's daily streak, and the pod gets a push notification when someone goes quiet for 24h
- **Student mode** — opt in at signup for Panhellenic (πανελλήνιες) exam tooling: a countdown to the exams and a subject-weighted view of whether your study hours match what each subject is worth

### Streaks

A day counts toward your streak if you completed at least one task **or** logged at least one study session that day (UTC). Days are computed server-side from `tasks.completed_at` and `study_sessions.occurred_at`, so a streak is consistent across devices and visible to your pod. Not having logged anything *yet today* does not break a streak — it only breaks after a full day passes with no activity.

## Tech Stack

- **Backend:** Python 3.11, FastAPI, SQLModel (async, on SQLAlchemy 2.0 core), Alembic, Pydantic v2
- **Frontend:** TypeScript, Next.js (App Router)
- **Database:** PostgreSQL 15
- **Architecture:** Layered — API routers → services → models/schemas

## Project Structure

```
backend/
  app/
    api/routers/     # FastAPI endpoints (auth, notes, tasks, pods,
                     #   exam_prep, push_subscriptions)
    services/         # Business logic
    models/           # SQLModel ORM models
    schemas/          # Pydantic request/response schemas
    core/             # Config, db session, security, exceptions
  migrations/         # Alembic migrations
  scripts/            # Operational scripts (exam subject/date seeding)
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

## Exam configuration (student mode)

> ⚠️ **The seeded exam date and subject weight coefficients are placeholders and are not verified.**
> Panhellenic coefficients and exam dates are set each year by ministry decision (ΦΕΚ) and differ
> between years and between scientific fields (επιστημονικά πεδία). Verify them against the current
> year's official decision before students plan around them.

The subjects, their weight coefficients, and the exam date live in the database
(`exam_subjects` / `exam_configs`) rather than in code, so they can be corrected each season
without a code change. The initial rows are seeded by the `c1a7d3f90b21` migration.

To edit them, change the constants at the top of `backend/scripts/seed_exam_config.py` and run:

```bash
make seed-exam
# or: cd backend && python -m scripts.seed_exam_config
```

The script upserts by subject `code` and track, so it is safe to run repeatedly. A subject removed
from the list is deactivated rather than deleted, keeping historical study sessions readable.

Only the Group D track (Οικονομίας & Πληροφορικής) is seeded today: Νεοελληνική Γλώσσα και
Λογοτεχνία, Μαθηματικά, ΑΕΠΠ, and Αρχές Οικονομικής Θεωρίας.

## Testing

```bash
cd backend
pytest
```

Tests build their schema from model metadata, so they do not exercise the migration files.
CI covers that separately by running `alembic upgrade head`, then `alembic check` (asserting the
models still match the migrations), then a full `downgrade base` / `upgrade head` round trip.
Run the same checks locally with:

```bash
cd backend
alembic upgrade head && alembic check
```

## Continuous Integration

`.github/workflows/ci.yml` runs three jobs: backend tests, the migration checks above, and a
frontend typecheck + build. `.github/workflows/cd.yml` builds and pushes production images.

Both workflows are currently **manual-trigger only** (`workflow_dispatch`); the push/pull_request
triggers are commented out, and CD additionally needs the `REGISTRY`, `REGISTRY_USERNAME`, and
`REGISTRY_PASSWORD` secrets before it will work.

> Note: ESLint is not configured in this project (no config file and no `eslint` dependency), so
> `npm run lint` drops into an interactive setup prompt and cannot pass in CI. CI runs
> `npm run typecheck` instead. Configure ESLint to restore linting.

## Production

`docker-compose.prod.yml` builds production images for the backend and frontend behind the Nginx reverse proxy config in `nginx/`.
