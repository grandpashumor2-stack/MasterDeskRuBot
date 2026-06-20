import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.redis import RedisStorage
from app.core.config import settings
from app.bot.handlers.client import router as client_router
from app.bot.handlers.owner import router as owner_router

logger = logging.getLogger(__name__)

async def main():
    bot = Bot(token=settings.BOT_TOKEN)
    storage = RedisStorage.from_url(settings.REDIS_URL)
    dp = Dispatcher(storage=storage)
    dp.include_router(client_router)
    dp.include_router(owner_router)
    logger.info("Bot starting...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
