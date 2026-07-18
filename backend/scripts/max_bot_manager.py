
"""
Бот МастерДеск для мессенджера MAX.

Реализовано:
- Платформенный экран (продающий питч + кнопки "Подключить"/"Демо"/"Тарифы")
- Привязка к конкретному автосервису по диплинку (?start=slug) или по
  введённому вручную коду
- Разделы "Наши услуги", "Цены", "Контакты" для привязанного автосервиса
- Полноценная запись на ремонт: выбор услуги -> марка/модель авто ->
  выбор свободного времени -> телефон -> создание appointment в БД

Запуск: MAX_BOT_TOKEN=... python scripts/max_bot_manager.py
"""
import sys
sys.path.insert(0, "/app")

import asyncio
import logging
from datetime import datetime, timedelta

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

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.infrastructure.database.connection import AsyncSessionLocal
from app.domain.repositories.company import CompanyRepository
from app.domain.repositories.service import ServiceRepository
from app.domain.repositories.client import ClientRepository
from app.domain.repositories.appointment import AppointmentRepository
from app.domain.models.service import PriceType
from app.domain.models.company import Company
from app.domain.models.appointment import Appointment, AppointmentSource, AppointmentStatus
from app.domain.models.client import Vehicle
from app.domain.models.analytics import AnalyticsEvent, EventType
from app.domain.services.booking import BookingService
from app.domain.services.subscription_checker import SubscriptionChecker

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot()
dp = Dispatcher()


class Flow(StatesGroup):
    waiting_company_code = State()
    waiting_service = State()
    waiting_car_info = State()
    waiting_time_slot = State()
    waiting_phone = State()


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
CB_SERVICE_PREFIX = "svc:"
CB_SLOT_PREFIX = "slot:"

DAY_NAMES = {
    0: "Понедельник", 1: "Вторник", 2: "Среда",
    3: "Четверг", 4: "Пятница", 5: "Суббота", 6: "Воскресенье",
}


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


def services_keyboard(services: list) -> InlineKeyboardBuilder:
    kb = InlineKeyboardBuilder()
    for svc in services:
        kb.row(CallbackButton(text=svc.name, payload=f"{CB_SERVICE_PREFIX}{svc.id}"))
    return kb


def day_label_for(d, today) -> str:
    if d == today:
        return "Сегодня"
    if d == today + timedelta(days=1):
        return "Завтра"
    return f"{DAY_NAMES[d.weekday()]} {d.strftime('%d.%m')}"


def slots_keyboard(slots: dict) -> InlineKeyboardBuilder:
    kb = InlineKeyboardBuilder()
    today = (datetime.utcnow() + timedelta(hours=3)).date()  # МСК
    for d, times in list(slots.items())[:3]:
        label = day_label_for(d, today)
        row_buttons = []
        for t in times[:4]:
            row_buttons.append(
                CallbackButton(
                    text=f"{label} {t.strftime('%H:%M')}",
                    payload=f"{CB_SLOT_PREFIX}{d.isoformat()}:{t.strftime('%H:%M')}",
                )
            )
        for i in range(0, len(row_buttons), 2):
            kb.row(*row_buttons[i:i + 2])
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


async def get_or_create_max_client(session, company, user):
    repo = ClientRepository(session)
    client = await repo.get_by_max_id(company.id, str(user.user_id))
    if not client:
        full_name = user.first_name or "Клиент MAX"
        if getattr(user, "last_name", None):
            full_name = f"{full_name} {user.last_name}"
        client = await repo.create(
            company_id=company.id,
            max_id=str(user.user_id),
            full_name=full_name,
        )
    return client


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
async def start_booking(event: MessageCreated, context: BaseContext) -> None:
    company = await get_context_company(context)
    if not company:
        await event.message.answer(
            text=WELCOME_TEXT,
            format=TextFormat.MARKDOWN,
            attachments=[main_keyboard().as_markup()],
        )
        return

    async with AsyncSessionLocal() as session:
        checker = SubscriptionChecker(session)
        if not await checker.is_active(company.id):
            await event.message.answer(
                text="Сервис временно недоступен. Обратитесь напрямую.",
                attachments=[company_main_keyboard().as_markup()],
            )
            return

        svc_repo = ServiceRepository(session)
        services = await svc_repo.get_company_services(company.id)

    if not services:
        await event.message.answer(
            text="Услуги пока не добавлены. Свяжитесь с нами напрямую.",
            attachments=[company_main_keyboard().as_markup()],
        )
        return

    await context.update_data(company_slug=company.slug)
    await context.set_state(Flow.waiting_service)
    await event.message.answer(
        text="Выберите услугу:",
        attachments=[services_keyboard(services).as_markup()],
    )


@dp.message_created(Flow.waiting_car_info, F.message.body.text)
async def on_car_info(event: MessageCreated, context: BaseContext) -> None:
    company = await get_context_company(context)
    if not company:
        await context.set_state(None)
        await event.message.answer(
            text=WELCOME_TEXT,
            format=TextFormat.MARKDOWN,
            attachments=[main_keyboard().as_markup()],
        )
        return

    car_info = (event.message.body.text or "").strip()
    await context.update_data(car_info=car_info)
    data = await context.get_data()
    duration = data.get("duration", 60)

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Company).options(selectinload(Company.working_hours)).where(Company.id == company.id)
        )
        company_wh = result.scalar_one_or_none()
        booking_svc = BookingService(session)
        slots = await booking_svc.get_available_slots(
            company.id,
            company_wh.working_hours if company_wh else [],
            duration_minutes=duration,
        )
        msg_text = booking_svc.format_slots_message(slots)

    if not slots:
        await event.message.answer(
            text=(
                f"К сожалению, свободных мест нет на ближайшие дни.\n"
                f"Позвоните нам: {company.phone or 'номер не указан'}"
            ),
            attachments=[company_main_keyboard().as_markup()],
        )
        await context.set_state(None)
        return

    await event.message.answer(
        text=msg_text,
        format=TextFormat.MARKDOWN,
        attachments=[slots_keyboard(slots).as_markup()],
    )
    await context.set_state(Flow.waiting_time_slot)


@dp.message_created(Flow.waiting_phone, F.message.body.text)
async def on_phone_text(event: MessageCreated, context: BaseContext) -> None:
    company = await get_context_company(context)
    if not company:
        await context.set_state(None)
        await event.message.answer(
            text=WELCOME_TEXT,
            format=TextFormat.MARKDOWN,
            attachments=[main_keyboard().as_markup()],
        )
        return

    phone = (event.message.body.text or "").strip()
    if not any(ch.isdigit() for ch in phone):
        await event.message.answer("Пожалуйста, введите номер телефона в сообщении.")
        return

    await create_appointment_and_confirm(event, context, company, phone)


async def create_appointment_and_confirm(event: MessageCreated, context: BaseContext, company, phone: str) -> None:
    data = await context.get_data()
    dt_str = f"{data.get('selected_date')} {data.get('selected_time')}"
    scheduled_at = datetime.strptime(dt_str, "%Y-%m-%d %H:%M")

    async with AsyncSessionLocal() as session:
        client = await get_or_create_max_client(session, company, event.message.sender)
        client.phone = phone
        client.visit_count = (client.visit_count or 0) + 1
        client.last_visit_at = datetime.utcnow()

        existing = await session.execute(
            select(Appointment).where(
                Appointment.company_id == company.id,
                Appointment.scheduled_at == scheduled_at,
                Appointment.status.notin_([AppointmentStatus.CANCELLED, AppointmentStatus.NO_SHOW]),
            )
        )
        if existing.scalar_one_or_none():
            await event.message.answer(
                text="К сожалению, это время только что заняли. Пожалуйста, выберите другое время — нажмите «Записаться» ещё раз.",
                attachments=[company_main_keyboard().as_markup()],
            )
            await context.set_state(None)
            return

        apt_repo = AppointmentRepository(session)
        appointment = await apt_repo.create(
            company_id=company.id,
            client_id=client.id,
            service_id=data.get("service_id"),
            scheduled_at=scheduled_at,
            duration_minutes=data.get("duration", 60),
            client_phone=phone,
            client_name=client.full_name,
            car_description=data.get("car_info"),
            source=AppointmentSource.MAX_BOT,
        )

        car_info = data.get("car_info", "")
        if car_info:
            parts = car_info.split()
            year = next((int(p) for p in parts if p.isdigit() and len(p) == 4), None)
            make = parts[0] if parts else None
            if year and len(parts) > 2:
                model = " ".join(parts[1:-1])
            elif len(parts) > 1:
                model = " ".join(parts[1:])
            else:
                model = None
            session.add(Vehicle(client_id=client.id, make=make, model=model, year=year))

        session.add(AnalyticsEvent(
            company_id=company.id,
            event_type=EventType.APPOINTMENT_CREATED,
            data={"appointment_id": str(appointment.id), "service": data.get("service_name")},
        ))

        await session.commit()

    confirmation = (
        f"✅ **Запись создана!**\n\n"
        f"📋 Услуга: {data.get('service_name', 'Не указана')}\n"
        f"🚗 Автомобиль: {data.get('car_info', 'Не указан')}\n"
        f"📅 Дата и время: {scheduled_at.strftime('%d.%m.%Y в %H:%M')}\n"
        f"📞 Телефон: {phone}\n\n"
        f"Мы напомним вам за 24 часа и за 2 часа до визита.\n"
        f"Ждём вас! 🚗"
    )
    await event.message.answer(
        text=confirmation,
        format=TextFormat.MARKDOWN,
        attachments=[company_main_keyboard().as_markup()],
    )
    await context.set_state(None)


@dp.message_callback()
async def on_callback(event: MessageCallback, context: BaseContext) -> None:
    payload = event.callback.payload if event.callback else None
    if event.message is None or payload is None:
        await event.answer()
        return

    if payload == CB_PRICING:
        await event.edit(
            text=PRICING_TEXT,
            format=TextFormat.MARKDOWN,
            attachments=[pricing_keyboard().as_markup()],
        )
        await event.answer()
        return

    if payload == CB_BACK:
        await event.edit(
            text=WELCOME_TEXT,
            format=TextFormat.MARKDOWN,
            attachments=[main_keyboard().as_markup()],
        )
        await event.answer()
        return

    if payload.startswith(CB_SERVICE_PREFIX):
        service_id = payload[len(CB_SERVICE_PREFIX):]
        company = await get_context_company(context)
        if not company:
            await event.answer()
            return
        async with AsyncSessionLocal() as session:
            svc_repo = ServiceRepository(session)
            service = await svc_repo.get(service_id)
        if not service:
            await event.answer()
            return
        await context.update_data(
            service_id=str(service.id),
            service_name=service.name,
            duration=service.duration_minutes or 60,
        )
        await context.set_state(Flow.waiting_car_info)
        await event.edit(
            text=(
                f"✅ Выбрано: **{service.name}**\n\n"
                f"Укажите марку и модель вашего автомобиля\n(например: Toyota Camry 2019)"
            ),
            format=TextFormat.MARKDOWN,
        )
        await event.answer()
        return

    if payload.startswith(CB_SLOT_PREFIX):
        rest = payload[len(CB_SLOT_PREFIX):]
        selected_date, selected_time = rest.split(":", 1)
        await context.update_data(selected_date=selected_date, selected_time=selected_time)
        await context.set_state(Flow.waiting_phone)
        await event.edit(
            text=f"Выбрано время: **{selected_date} {selected_time}**\n\nТеперь укажите ваш номер телефона сообщением.",
            format=TextFormat.MARKDOWN,
        )
        await event.answer()
        return

    await event.answer()


async def main() -> None:
    logger.info("Starting MAX bot (МастерДеск)...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
