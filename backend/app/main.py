import asyncio
import contextlib

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.applications import router as applications_router
from app.api.v1.auth import router as auth_router, session_router
from app.api.v1.events import router as events_router
from app.api.v1.gmail import router as gmail_router
from app.api.v1.review_items import router as review_items_router
from app.api.v1.opportunities import router as opportunities_router
from app.api.v1.matching import router as matching_router
from app.api.v1.preparations import router as preparations_router
from app.core.error_handlers import register_error_handlers
from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models import GmailConnection
from app.services.gmail_sync_service import sync_gmail_connection
from sqlalchemy import select


async def gmail_sync_loop() -> None:
    settings = get_settings()
    while True:
        await asyncio.sleep(settings.gmail_sync_interval_seconds)
        if not settings.gmail_sync_enabled:
            continue
        with SessionLocal() as db:
            connections = db.scalars(select(GmailConnection).where(GmailConnection.connection_status == "CONNECTED")).all()
            for connection in connections:
                try:
                    sync_gmail_connection(db, user_id=connection.user_id, connection_id=connection.id)
                except Exception:
                    db.rollback()


@contextlib.asynccontextmanager
async def lifespan(_: FastAPI):
    task = asyncio.create_task(gmail_sync_loop())
    try:
        yield
    finally:
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task


app = FastAPI(
    title="JobTrack API",
    description="Intelligent Job Application Tracking System",
    version="0.1.0",
    lifespan=lifespan,
)
register_error_handlers(app)

allowed_origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Content-Type", "X-CSRF-Token"],
)

app.include_router(applications_router, prefix="/api/v1")
app.include_router(events_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1")
app.include_router(session_router, prefix="/api/v1")
app.include_router(gmail_router, prefix="/api/v1")
app.include_router(review_items_router, prefix="/api/v1")
app.include_router(opportunities_router, prefix="/api/v1")
app.include_router(matching_router, prefix="/api/v1")
app.include_router(preparations_router, prefix="/api/v1")


@app.get("/api/health", tags=["Health"])
def health_check():
    return {
        "status": "healthy",
        "service": "jobtrack-backend",
        "version": "0.1.0",
    }