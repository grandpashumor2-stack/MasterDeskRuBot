from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message
from sqlalchemy.ext.asyncio import AsyncSession
from app.domain.repositories.company import CompanyRepository
from app.infrastructure.database.connection import AsyncSessionLocal


class CompanyMiddleware(BaseMiddleware):
    """Resolve company by bot token for each update."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        bot = data.get("bot")
        if bot:
            async with AsyncSessionLocal() as session:
                repo = CompanyRepository(session)
                company = await repo.get_by_bot_token(bot.token)
                data["company"] = company
                data["db_session"] = session
                return await handler(event, data)
        return await handler(event, data)
