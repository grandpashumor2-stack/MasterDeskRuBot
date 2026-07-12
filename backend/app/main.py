from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import logging

from app.core.config import settings
from app.api.v1.router import api_router
from app.web.panel import web_router
from app.infrastructure.database.connection import engine
from app.domain.models import *  # noqa: ensure all models are loaded

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting AutoService AI Manager...")
    
    
    yield
    
    # Shutdown
    await engine.dispose()
    logger.info("Shutdown complete.")


app = FastAPI(
    title="AutoService AI Manager",
    version=settings.APP_VERSION,
    description="SaaS платформа для автосервисов России",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API routes
app.include_router(api_router)

# Web panel routes
app.include_router(web_router)

# Static files
app.mount("/static", StaticFiles(directory="app/web/static"), name="static")


@app.get("/health")
async def health():
    return {"status": "ok", "version": settings.APP_VERSION}
