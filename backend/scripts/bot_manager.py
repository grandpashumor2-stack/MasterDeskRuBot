import sys
sys.path.insert(0, "/app")
"""
Bot Manager — запускает отдельный экземпляр aiogram для каждого автосервиса.
Также запускает платформенный демо-бот @MasterDeskRuBot если задан BOT_TOKEN.
"""
import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from app.core.config import settings
from app.bot.handlers.client import router as client_router
from app.bot.handlers.owner import router as owner_router
from app.bot.middlewares.company import CompanyMiddleware

logger = logging.getLogger(__name__)


class BotInstance:
    def __init__(self, token: str, company_id: str | None = None):
        self.token = token
        self.company_id = company_id
        self.bot: Bot | None = None
        self.dp: Dispatcher | None = None
        self.task: asyncio.Task | None = None

    async def start(self):
        storage = RedisStorage.from_url(settings.REDIS_URL)
        self.bot = Bot(
            token=self.token,
            default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN)
        )
        self.dp = Dispatcher(storage=storage)
        self.dp.message.middleware(CompanyMiddleware())
        self.dp.callback_query.middleware(CompanyMiddleware())
        self.dp.include_router(owner_router)
        self.dp.include_router(client_router)

        try:
            me = await self.bot.get_me()
            logger.info(f"✅ Bot @{me.username} started (company: {self.company_id or 'platform demo'})")
            await self.dp.start_polling(self.bot, allowed_updates=["message", "callback_query"])
        except Exception as e:
            logger.error(f"Bot error [{self.token[:15]}...]: {e}")
        finally:
            if self.bot:
                await self.bot.session.close()

    async def stop(self):
        if self.dp:
            await self.dp.stop_polling()
        if self.bot:
            await self.bot.session.close()


class BotManager:
    def __init__(self):
        self.instances: dict[str, BotInstance] = {}

    async def add_bot(self, token: str, company_id: str | None = None):
        if token in self.instances:
            return
        instance = BotInstance(token, company_id)
        self.instances[token] = instance
        task = asyncio.create_task(instance.start())
        instance.task = task

    async def remove_bot(self, token: str):
        instance = self.instances.pop(token, None)
        if instance:
            await instance.stop()
            if instance.task:
                instance.task.cancel()

    async def load_company_bots(self):
        """Load all active bot tokens from DB."""
        from app.infrastructure.database.connection import AsyncSessionLocal
        from app.domain.models.company import Company
        from sqlalchemy import select

        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Company).where(
                    Company.is_active == True,
                    Company.telegram_bot_token.isnot(None),
                )
            )
            companies = list(result.scalars().all())

        for company in companies:
            await self.add_bot(company.telegram_bot_token, str(company.id))
        
        logger.info(f"Loaded {len(companies)} company bots from DB")

    async def sync_loop(self):
        """Periodically sync bots from DB (every 60 sec)."""
        while True:
            await asyncio.sleep(60)
            try:
                from app.infrastructure.database.connection import AsyncSessionLocal
                from app.domain.models.company import Company
                from sqlalchemy import select

                async with AsyncSessionLocal() as session:
                    result = await session.execute(
                        select(Company.telegram_bot_token, Company.id).where(
                            Company.is_active == True,
                            Company.telegram_bot_token.isnot(None),
                        )
                    )
                    rows = result.all()

                active = {row[0]: str(row[1]) for row in rows}
                # Keep platform demo bot always
                platform_token = settings.BOT_TOKEN
                if platform_token:
                    active[platform_token] = None

                # Add new
                for token, cid in active.items():
                    if token not in self.instances:
                        logger.info(f"New bot detected, starting...")
                        await self.add_bot(token, cid)

                # Remove deleted
                for token in [t for t in self.instances if t not in active]:
                    logger.info(f"Bot removed from DB, stopping...")
                    await self.remove_bot(token)

            except Exception as e:
                logger.error(f"Sync error: {e}")

    async def run(self):
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s %(levelname)s %(name)s: %(message)s"
        )
        logger.info("🚀 MasterDesk Bot Manager starting...")

        # 1. Start platform demo bot (@MasterDeskRuBot)
        if settings.BOT_TOKEN:
            logger.info("Starting platform demo bot @MasterDeskRuBot...")
            await self.add_bot(settings.BOT_TOKEN, None)
        else:
            logger.warning("BOT_TOKEN not set — platform demo bot won't start")

        # 2. Load all company bots from DB
        await self.load_company_bots()

        # 3. Run sync loop forever
        await self.sync_loop()


if __name__ == "__main__":
    manager = BotManager()
    asyncio.run(manager.run())
