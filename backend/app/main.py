from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import logging

from app.core.config import settings
from app.api.v1.router import api_router
from app.web.panel import web_router
from app.infrastructure.scheduler.tasks import setup_scheduler
from app.infrastructure.database.connection import engine
from app.domain.models import *  # noqa

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Запуск МастерДеск...")
    scheduler = setup_scheduler()
    yield
    scheduler.shutdown()
    await engine.dispose()
    logger.info("Остановлен.")


app = FastAPI(
    title="МастерДеск",
    version="1.0.0",
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

app.include_router(api_router)
app.include_router(web_router)
app.mount("/static", StaticFiles(directory="app/web/static"), name="static")


@app.get("/health")
async def health():
    return {"status": "ok", "app": settings.APP_NAME}
