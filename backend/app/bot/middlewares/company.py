from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from app.domain.repositories.company import CompanyRepository
from app.infrastructure.database.connection import AsyncSessionLocal


class CompanyMiddleware(BaseMiddleware):
    """Resolve company by bot token or by user's saved company code."""

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
                # 1. Сначала ищем по токену бота (для мультибот режима)
                company = await repo.get_by_bot_token(bot.token)
                # 2. Если не нашли — ищем по коду из FSM state
                if not company:
                    state: FSMContext = data.get("state")
                    if state:
                        state_data = await state.get_data()
                        slug = state_data.get("company_slug")
                        if slug:
                            company = await repo.get_by_slug(slug)
                data["company"] = company
                data["db_session"] = session
                return await handler(event, data)
        return await handler(event, data)
