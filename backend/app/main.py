from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routers import auth, notes, push_subscriptions, tasks
from app.core.config import settings
from app.core.exceptions import ConflictError, NotFoundError
from app.services.notification_service import send_due_task_notifications


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    scheduler = AsyncIOScheduler()
    scheduler.add_job(send_due_task_notifications, "interval", seconds=60)
    scheduler.start()
    yield
    scheduler.shutdown()


app = FastAPI(title="Note of Accountability API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(NotFoundError)
async def not_found_handler(request: Request, exc: NotFoundError) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": str(exc)})


@app.exception_handler(ConflictError)
async def conflict_handler(request: Request, exc: ConflictError) -> JSONResponse:
    return JSONResponse(status_code=409, content={"detail": str(exc)})


app.include_router(auth.router)
app.include_router(notes.router)
app.include_router(tasks.router)
app.include_router(push_subscriptions.router)


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok"}
