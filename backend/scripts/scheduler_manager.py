"""
Standalone entrypoint for the background scheduler (APScheduler).

Why this is its own process (not started inside the API):
Previously the scheduler was started in FastAPI's lifespan (app/main.py).
That's fine with a single uvicorn worker, but the moment the API is scaled
to 2+ workers, EACH worker process starts its own copy of the scheduler —
which already caused a real production bug once (payments and reminders
were processed twice). Running the scheduler as its own container means
the API can be scaled to multiple workers freely, while the scheduler
always runs in exactly one process, no matter what.

Run with: python scripts/scheduler_manager.py
"""
import sys
sys.path.insert(0, "/app")

import asyncio
import logging
import signal

from app.infrastructure.scheduler.tasks import setup_scheduler
from app.infrastructure.database.connection import engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    logger.info("Starting standalone scheduler process...")
    scheduler = setup_scheduler()
    logger.info("Scheduler started. Jobs: %s", [job.id for job in scheduler.get_jobs()])

    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, stop_event.set)

    await stop_event.wait()

    logger.info("Shutdown signal received, stopping scheduler...")
    scheduler.shutdown(wait=False)
    await engine.dispose()
    logger.info("Scheduler shutdown complete.")


if __name__ == "__main__":
    asyncio.run(main())
