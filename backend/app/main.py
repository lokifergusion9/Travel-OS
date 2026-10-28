"""TravelOS FastAPI application entrypoint."""
from contextlib import asynccontextmanager

import logging
import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.v1 import api_router
from app.core.config import settings

# Surface our own loggers (message sends, scheduler) on stdout — uvicorn's
# config otherwise hides non-uvicorn loggers.
_handler = logging.StreamHandler(sys.stdout)
_handler.setFormatter(logging.Formatter("%(levelname)s [%(name)s] %(message)s"))
_travelos_log = logging.getLogger("travelos")
_travelos_log.setLevel(logging.INFO)
_travelos_log.addHandler(_handler)
_travelos_log.propagate = False


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.require_production_secrets()
    from app.workers.scheduler import start_scheduler, stop_scheduler

    # In multi-worker prod the scheduler runs as a dedicated worker process; the
    # web service sets RUN_SCHEDULER=false to avoid duplicating jobs.
    if settings.run_scheduler:
        start_scheduler()
    try:
        yield
    finally:
        if settings.run_scheduler:
            stop_scheduler()


app = FastAPI(
    title="TravelOS API",
    version="0.1.0",
    description="AI-powered multi-tenant travel CRM & operations platform.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)

# Serve generated creatives (posters, brochures) in dev. S3+CDN in prod.
_storage_dir = Path(settings.storage_dir)
_storage_dir.mkdir(parents=True, exist_ok=True)
app.mount("/storage", StaticFiles(directory=str(_storage_dir)), name="storage")


@app.get("/health", tags=["meta"])
async def health() -> dict[str, str]:
    return {"status": "ok", "environment": settings.environment}


@app.get("/", tags=["meta"])
async def root() -> dict[str, str]:
    return {"service": "TravelOS API", "docs": "/docs"}
