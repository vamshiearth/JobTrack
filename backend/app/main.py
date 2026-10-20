from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.applications import router as applications_router


app = FastAPI(
    title="JobTrack API",
    description="Intelligent Job Application Tracking System",
    version="0.1.0",
)

allowed_origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET"],
    allow_headers=["Content-Type"],
)

app.include_router(applications_router, prefix="/api/v1")


@app.get("/api/health", tags=["Health"])
def health_check():
    return {
        "status": "healthy",
        "service": "jobtrack-backend",
        "version": "0.1.0",
    }