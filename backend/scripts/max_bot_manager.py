"""
Бот МастерДеск для мессенджера MAX.

Реализовано:
- Платформенный экран (продающий питч + кнопки "Подключить"/"Демо"/"Тарифы")
- Привязка к конкретному автосервису по диплинку (?start=slug) или по
  введённому вручную коду
- Разделы "Наши услуги", "Цены", "Контакты" для привязанного автосервиса

Пока не реализовано (следующий отдельный шаг):
- Сама запись на услугу (выбор времени, телефон, подтверждение)

Запуск: MAX_BOT_TOKEN=... python scripts/max_bot_manager.py
"""
import sys
sys.path.insert(0, "/app")

import asyncio
import logging

from maxapi import Bot, Dispatcher, F
from maxapi.context.base import BaseContext
from maxapi.context.state_machine import State, StatesGroup
from maxapi.enums.parse_mode import TextFormat
from maxapi.filters.command import CommandStart
from maxapi.types.attachments.buttons.callback_button import CallbackButton
from maxapi.types.attachments.buttons.link_button import LinkButton
from maxapi.types.attachments.buttons.message_button import MessageButton
from maxapi.types.updates.bot_started import BotStarted
from maxapi.types.updates.message_callback import MessageCallback
from maxapi.types.updates.message_created import MessageCreated
from maxapi.utils.inline_keyboard import InlineKeyboardBuilder

from app.infrastructure.database.connection import AsyncSessionLocal
from app.domain.repositories.company import CompanyRepository
from app.domain.repositories.service import ServiceRepository
from app.domain.models.service import PriceType

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot()
dp = Dispatcher()


class Flow(StatesGroup):
    waiting_company_code = State()


WELCOME_TEXT = (
    "👋 **Добро пожаловать в МастерДеск**\n\n"
    "Не теряйте клиентов вечером и в выходные — МастерДеск сам "
    "принимает заявки и записывает клиентов 24/7.\n\n"
    "Что вы получите:\n\n"
    "✅ Онлайн-запись клиентов\n"
    "✅ Управление услугами и ценами\n"
    "✅ Напоминания клиентам\n"
    "✅ Возврат клиентов на обслуживание\n"
    "✅ Подключение за 5 минут\n\n"
    "🎁 1 месяц бесплатно\n\n"
    "Уже клиент автосервиса? Введите его код сообщением."
)

PRICING_TEXT = (
    "💰 **Тарифы МастерДеск**\n\n"
    "🚗 **Старт** — 1490 ₽/мес\n"
    "🔧 **Бизнес** — 2990 ₽/мес\n"
    "⭐ **Премиум** — 5990 ₽/мес\n\n"
    "🎁 Первый месяц — бесплатно на любом тарифе.\n"
    "Точный список функций каждого тарифа — на странице регистрации."
)

COMPANY_WELCOME_TEMPLATE = (
    "👋 **Добро пожаловать в {name}**!\n\n"
    "Я — ваш виртуальный администратор. Помогу:\n"
    "• Узнать цены на услуги\n"
    "• Записаться на ремонт\n\n"
    "Выберите действие ⬇️"
)

CB_PRICING = "pricing"
CB_BACK = "back_to_start"


def main_keyboard() -> InlineKeyboardBuilder:
    kb = InlineKeyboardBuilder()
    kb.row(LinkButton(text="🚗 Подключить автосервис", url="https://master-desk.ru/register"))
    kb.row(LinkButton(text="📹 Посмотреть демо", url="https://master-desk.ru/demo"))
    kb.row(CallbackButton(text="💰 Тарифы", payload=CB_PRICING))
    return kb


def pricing_keyboard() -> InlineKeyboardBuilder:
    kb = InlineKeyboardBuilder()
    kb.row(LinkButton(text="🚗 Подключить автосервис", url="https://master-desk.ru/register"))
    kb.row(CallbackButton(text="◀️ Назад", payload=CB_BACK))
    return kb


def company_main_keyboard() -> InlineKeyboardBuilder:
    kb = InlineKeyboardBuilder()
    kb.row(MessageButton(text="📅 Записаться"), MessageButton(text="📋 Наши услуги"))
    kb.row(MessageButton(text="💰 Цены"), MessageButton(text="📞 Контакты"))
    return kb


async def get_company_by_slug(slug: str):
    slug = (slug or "").strip().lower()
    if not slug:
        return None
    async with AsyncSessionLocal() as session:
        repo = CompanyRepository(session)
        return await repo.get_by_slug(slug)


async def get_context_company(context: BaseContext):
    data = await context.get_data()
    slug = data.get("company_slug")
    if not slug:
        return None
    return await get_company_by_slug(slug)


async def enter_company(context: BaseContext, slug: str):
    company = await get_company_by_slug(slug)
    if company:
        await context.set_state(None)
        await context.update_data(company_slug=company.slug)
    return company


@dp.bot_started()
async def on_bot_started(event: BotStarted, context: BaseContext) -> None:
    company = await enter_company(context, event.payload or "")
    if company:
        await bot.send_message(
            user_id=event.user.user_id,
            text=COMPANY_WELCOME_TEMPLATE.format(name=company.name),
            format=TextFormat.MARKDOWN,
            attachments=[company_main_keyboard().as_markup()],
        )
        return

    await context.set_state(Flow.waiting_company_code)
    await bot.send_message(
        user_id=event.user.user_id,
        text=WELCOME_TEXT,
        format=TextFormat.MARKDOWN,
        attachments=[main_keyboard().as_markup()],
    )


@dp.message_created(CommandStart())
async def on_start(event: MessageCreated, context: BaseContext, args: list | None = None) -> None:
    slug = args[0] if args else ""
    company = await enter_company(context, slug)
    if company:
        await event.message.answer(
            text=COMPANY_WELCOME_TEMPLATE.format(name=company.name),
            format=TextFormat.MARKDOWN,
            attachments=[company_main_keyboard().as_markup()],
        )
        return

    await context.set_state(Flow.waiting_company_code)
    await event.message.answer(
        text=WELCOME_TEXT,
        format=TextFormat.MARKDOWN,
        attachments=[main_keyboard().as_markup()],
    )


@dp.message_created(Flow.waiting_company_code, F.message.body.text)
async def on_company_code(event: MessageCreated, context: BaseContext) -> None:
    raw = (event.message.body.text or "").strip() if event.message.body else ""
    if not raw:
        return
    company = await enter_company(context, raw)
    if not company:
        await event.message.answer("Автосервис с таким кодом не найден. Проверьте код и попробуйте ещё раз.")
        return
    await event.message.answer(
        text=COMPANY_WELCOME_TEMPLATE.format(name=company.name),
        format=TextFormat.MARKDOWN,
        attachments=[company_main_keyboard().as_markup()],
    )


@dp.message_callback()
async def on_callback(event: MessageCallback) -> None:
    payload = event.callback.payload if event.callback else None
    if event.message is None:
        await event.answer()
        return

    if payload == CB_PRICING:
        await event.edit(
            text=PRICING_TEXT,
            format=TextFormat.MARKDOWN,
            attachments=[pricing_keyboard().as_markup()],
        )
    elif payload == CB_BACK:
        await event.edit(
            text=WELCOME_TEXT,
            format=TextFormat.MARKDOWN,
            attachments=[main_keyboard().as_markup()],
        )

    await event.answer()


@dp.message_created(F.message.body.text == "📞 Контакты")
async def on_contacts(event: MessageCreated, context: BaseContext) -> None:
    company = await get_context_company(context)
    if not company:
        await event.message.answer(
            text=WELCOME_TEXT,
            format=TextFormat.MARKDOWN,
            attachments=[main_keyboard().as_markup()],
        )
        return

    text = f"📍 **{company.name}**\n\n"
    if company.address:
        text += f"📌 Адрес: {company.address}\n"
    if company.phone:
        text += f"📞 Телефон: {company.phone}\n"

    await event.message.answer(
        text=text,
        format=TextFormat.MARKDOWN,
        attachments=[company_main_keyboard().as_markup()],
    )


@dp.message_created(F.message.body.text == "📋 Наши услуги")
async def on_services(event: MessageCreated, context: BaseContext) -> None:
    company = await get_context_company(context)
    if not company:
        await event.message.answer(
            text=WELCOME_TEXT,
            format=TextFormat.MARKDOWN,
            attachments=[main_keyboard().as_markup()],
        )
        return

    async with AsyncSessionLocal() as session:
        svc_repo = ServiceRepository(session)
        services = await svc_repo.get_company_services(company.id)

    if not services:
        await event.message.answer(
            text="Услуги пока не добавлены. Свяжитесь с нами напрямую.",
            attachments=[company_main_keyboard().as_markup()],
        )
        return

    text = f"🔧 **Услуги {company.name}:**\n\n"
    for svc in services:
        text += f"• **{svc.name}**"
        if svc.duration_minutes:
            text += f" — {svc.duration_minutes} мин"
        if svc.prices:
            p = svc.prices[0]
            if p.price_type == PriceType.FIXED and p.fixed_price:
                text += f" — {int(p.fixed_price):,} ₽".replace(",", " ")
            elif p.price_type == PriceType.RANGE and p.price_min:
                text += f" — от {int(p.price_min):,} ₽".replace(",", " ")
        text += "\n"
    text += "\nНажмите **Записаться** для выбора услуги и времени."

    await event.message.answer(
        text=text,
        format=TextFormat.MARKDOWN,
        attachments=[company_main_keyboard().as_markup()],
    )


@dp.message_created(F.message.body.text == "💰 Цены")
async def on_prices(event: MessageCreated, context: BaseContext) -> None:
    company = await get_context_company(context)
    if not company:
        await event.message.answer(
            text=WELCOME_TEXT,
            format=TextFormat.MARKDOWN,
            attachments=[main_keyboard().as_markup()],
        )
        return

    async with AsyncSessionLocal() as session:
        svc_repo = ServiceRepository(session)
        services = await svc_repo.get_company_services(company.id)

    if not services:
        await event.message.answer(
            text="Прайс-лист пока не добавлен. Свяжитесь с нами напрямую.",
            attachments=[company_main_keyboard().as_markup()],
        )
        return

    text = f"💰 **Прайс-лист {company.name}:**\n\n"
    for svc in services:
        text += f"• **{svc.name}**"
        if svc.duration_minutes:
            text += f" ({svc.duration_minutes} мин)"
        if svc.prices:
            p = svc.prices[0]
            if p.price_type == PriceType.FIXED and p.fixed_price:
                text += f" — {int(p.fixed_price):,} ₽".replace(",", " ")
            elif p.price_type == PriceType.RANGE and p.price_min:
                text += f" — от {int(p.price_min):,} ₽".replace(",", " ")
            elif p.price_type == PriceType.ON_REQUEST:
                text += " — по запросу"
        text += "\n"
    text += "\n📅 Записаться на ремонт — нажмите **Записаться**"

    await event.message.answer(
        text=text,
        format=TextFormat.MARKDOWN,
        attachments=[company_main_keyboard().as_markup()],
    )


@dp.message_created(F.message.body.text == "📅 Записаться")
async def on_booking_placeholder(event: MessageCreated, context: BaseContext) -> None:
    company = await get_context_company(context)
    if not company:
        await event.message.answer(
            text=WELCOME_TEXT,
            format=TextFormat.MARKDOWN,
            attachments=[main_keyboard().as_markup()],
        )
        return

    await event.message.answer(
        text=(
            "📅 Запись через MAX появится в ближайшее время!\n\n"
            "Пока можно записаться через сайт: https://master-desk.ru/register\n"
            f"Телефон: {company.phone or 'уточните на сайте'}"
        ),
        attachments=[company_main_keyboard().as_markup()],
    )


async def main() -> None:
    logger.info("Starting MAX bot (МастерДеск)...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
