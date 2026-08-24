# Note of Accountability (NoA) - Tech Guidelines

## Product Vision
Note of Accountability (NoA) is a productivity & accountability system engineered for high-performance students/engineers. It unifies markdown notes, task tracking, daily schedules, and automated accountability metrics/notifications.


## Tech Stack
- Backend: Python 3.11, FastAPI, SQLModel (Async, on SQLAlchemy 2.0 core), Alembic, Pydantic v2
- Frontend: TypeScript, Next.js (App Router)
- Database: PostgreSQL 15
- Architecture: Layered Architecture (API -> Services -> Models/Schemas)


## Code Style & Rules
- Whenever i create a worktree with claude --w , i want the .env file to be copied 
- Always use type hints.
- Keep FastAPI endpoints thin. Business logic goes into service classes.
- All database operations must be async (`async/await`).
- Use Pydantic models for validation, SQLModel for ORM.
- Frontend code is TypeScript only — no plain `.js`/`.jsx` files.
- Never write hardcoded secrets; use environment variables via `pydantic-settings`.

## Commands
- Run backend: `uvicorn app.main:app --reload`
- Run migrations: `alembic upgrade head`
- Make migration: `alembic revision --autogenerate -m "description"`