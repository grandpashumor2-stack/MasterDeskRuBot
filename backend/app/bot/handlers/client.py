from datetime import datetime
from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery, Contact
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.states.booking import BookingStates
from app.bot.keyboards.client import (
    main_menu_keyboard, services_keyboard,
    time_slots_keyboard, confirm_booking_keyboard, share_phone_keyboard
)
from app.domain.models.company import Company
from app.domain.models.appointment import AppointmentSource
from app.domain.models.message import MessageDirection
from app.domain.repositories.client import ClientRepository
from app.domain.repositories.service import ServiceRepository
from app.domain.repositories.appointment import AppointmentRepository
from app.domain.services.booking import BookingService
from app.domain.services.subscription_checker import SubscriptionChecker
from app.infrastructure.ai import service as ai_service

router = Router()


async def get_or_create_client(session: AsyncSession, company: Company, message: Message):
    repo = ClientRepository(session)
    client = await repo.get_by_telegram_id(company.id, str(message.from_user.id))
    if not client:
        client = await repo.create(
            company_id=company.id,
            telegram_id=str(message.from_user.id),
            telegram_username=message.from_user.username,
            full_name=message.from_user.full_name,
        )
    return client


async def save_message(session: AsyncSession, company, client, text: str, direction: MessageDirection, is_ai: bool = False):
    from app.domain.models.message import Message as Msg
    msg = Msg(
        company_id=company.id,
        client_id=client.id if client else None,
        telegram_id=str(client.telegram_id) if client else None,
        direction=direction,
        text=text,
        is_ai_response=is_ai,
    )
    session.add(msg)


@router.message(CommandStart())
async def cmd_start(message: Message, company: Company, db_session: AsyncSession):
    if not company:
        await message.answer(
            "👋 Добро пожаловать в *МастерДеск*!\n\n"
            "🔧 Платформа для автоматизации автосервисов\n\n"
            "Если вы владелец автосервиса — зарегистрируйтесь на нашем сайте "
            "и подключите бота для своих клиентов.\n\n"
            "🌐 http://217.12.37.18",
            parse_mode="Markdown"
        )
        return
    
    client = await get_or_create_client(db_session, company, message)
    
    welcome = (
        f"👋 Добро пожаловать в *{company.name}*!\n\n"
        f"Я — ваш виртуальный администратор. Помогу:\n"
        f"• Узнать цены на услуги\n"
        f"• Записаться на ремонт\n"
        f"• Ответить на вопросы\n\n"
        f"Выберите действие или напишите ваш вопрос ⬇️"
    )
    await message.answer(welcome, reply_markup=main_menu_keyboard(), parse_mode="Markdown")


@router.message(F.text == "📋 Наши услуги")
async def show_services(message: Message, company: Company, db_session: AsyncSession):
    svc_repo = ServiceRepository(db_session)
    services = await svc_repo.get_company_services(company.id)
    if not services:
        await message.answer("Услуги пока не добавлены. Свяжитесь с нами напрямую.")
        return
    
    text = f"🔧 *Услуги {company.name}:*\n\n"
    for svc in services:
        text += f"• *{svc.name}*"
        if svc.duration_minutes:
            text += f" — {svc.duration_minutes} мин"
        if svc.prices:
            p = svc.prices[0]
            from app.domain.models.service import PriceType
            if p.price_type == PriceType.FIXED:
                text += f" — {int(p.fixed_price):,} ₽".replace(",", " ")
            elif p.price_type == PriceType.RANGE:
                text += f" — от {int(p.price_min):,} ₽".replace(",", " ")
        text += "\n"
    
    text += "\nНажмите *Записаться* для выбора услуги и времени."
    await message.answer(text, parse_mode="Markdown", reply_markup=main_menu_keyboard())


@router.message(F.text == "📅 Записаться")
async def start_booking(message: Message, state: FSMContext, company: Company, db_session: AsyncSession):
    checker = SubscriptionChecker(db_session)
    if not await checker.is_active(company.id):
        await message.answer("Сервис временно недоступен. Обратитесь напрямую.")
        return

    svc_repo = ServiceRepository(db_session)
    services = await svc_repo.get_company_services(company.id)
    if not services:
        await message.answer("Услуги пока не добавлены.")
        return

    await message.answer("Выберите услугу:", reply_markup=services_keyboard(services))
    await state.set_state(BookingStates.waiting_service)


@router.callback_query(F.data.startswith("book_service:"), BookingStates.waiting_service)
async def service_selected(callback: CallbackQuery, state: FSMContext, company: Company, db_session: AsyncSession):
    service_id = callback.data.split(":")[1]
    svc_repo = ServiceRepository(db_session)
    service = await svc_repo.get(service_id)
    
    if not service:
        await callback.answer("Услуга не найдена")
        return
    
    await state.update_data(service_id=str(service.id), service_name=service.name, duration=service.duration_minutes)
    await callback.message.edit_text(
        f"✅ Выбрано: *{service.name}*\n\nУкажите марку и модель вашего автомобиля\n(например: Toyota Camry 2019)",
        parse_mode="Markdown"
    )
    await state.set_state(BookingStates.waiting_car_info)


@router.message(BookingStates.waiting_car_info)
async def car_info_received(message: Message, state: FSMContext, company: Company, db_session: AsyncSession):
    await state.update_data(car_info=message.text)
    
    booking_svc = BookingService(db_session)
    company_full = await db_session.get(Company, company.id)
    from sqlalchemy.orm import selectinload
    from sqlalchemy import select
    result = await db_session.execute(
        select(Company).options(selectinload(Company.working_hours)).where(Company.id == company.id)
    )
    company_with_wh = result.scalar_one_or_none()
    
    data = await state.get_data()
    duration = data.get("duration", 60)
    
    slots = await booking_svc.get_available_slots(
        company.id, company_with_wh.working_hours if company_with_wh else [], duration_minutes=duration
    )
    
    if not slots:
        await message.answer(
            "К сожалению, свободных мест нет на ближайшие дни.\n"
            f"Позвоните нам: {company.phone or 'номер не указан'}",
            reply_markup=main_menu_keyboard()
        )
        await state.clear()
        return
    
    await state.update_data(available_slots=str(slots))
    msg_text = booking_svc.format_slots_message(slots)
    await message.answer(msg_text, reply_markup=time_slots_keyboard(slots), parse_mode="Markdown")
    await state.set_state(BookingStates.waiting_time_slot)


@router.callback_query(F.data.startswith("slot:"), BookingStates.waiting_time_slot)
async def slot_selected(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split(":")
    selected_date = parts[1]
    selected_time = parts[2]
    await state.update_data(selected_date=selected_date, selected_time=selected_time)
    await callback.message.edit_text(
        f"📅 Выбрано: *{selected_date} в {selected_time}*\n\n"
        "Пожалуйста, поделитесь номером телефона для подтверждения записи:",
        parse_mode="Markdown"
    )
    await callback.message.answer("👇", reply_markup=share_phone_keyboard())
    await state.set_state(BookingStates.waiting_phone)


@router.message(F.contact, BookingStates.waiting_phone)
async def phone_received(message: Message, state: FSMContext, company: Company, db_session: AsyncSession):
    phone = message.contact.phone_number
    await _create_appointment(message, state, company, db_session, phone)


@router.message(BookingStates.waiting_phone)
async def phone_text_received(message: Message, state: FSMContext, company: Company, db_session: AsyncSession):
    # Accept typed phone number
    phone = message.text.strip()
    if not any(c.isdigit() for c in phone):
        await message.answer("Пожалуйста, введите номер телефона или нажмите кнопку.")
        return
    await _create_appointment(message, state, company, db_session, phone)


async def _create_appointment(message: Message, state: FSMContext, company: Company, db_session: AsyncSession, phone: str):
    data = await state.get_data()
    
    client = await get_or_create_client(db_session, company, message)
    # Update phone
    client.phone = phone
    
    apt_repo = AppointmentRepository(db_session)
    
    from datetime import datetime
    dt_str = f"{data['selected_date']} {data['selected_time']}"
    scheduled_at = datetime.strptime(dt_str, "%Y-%m-%d %H:%M")
    
    appointment = await apt_repo.create(
        company_id=company.id,
        client_id=client.id,
        service_id=data.get("service_id"),
        scheduled_at=scheduled_at,
        duration_minutes=data.get("duration", 60),
        client_phone=phone,
        client_name=message.from_user.full_name,
        car_description=data.get("car_info"),
        source=AppointmentSource.TELEGRAM_BOT,
    )
    
    # Log analytics
    from app.domain.models.analytics import AnalyticsEvent, EventType
    event = AnalyticsEvent(
        company_id=company.id,
        event_type=EventType.APPOINTMENT_CREATED,
        data={"appointment_id": str(appointment.id), "service": data.get("service_name")},
    )
    db_session.add(event)
    
    confirmation = (
        f"✅ *Запись создана!*\n\n"
        f"📋 Услуга: {data.get('service_name', 'Не указана')}\n"
        f"🚗 Автомобиль: {data.get('car_info', 'Не указан')}\n"
        f"📅 Дата и время: {scheduled_at.strftime('%d.%m.%Y в %H:%M')}\n"
        f"📞 Телефон: {phone}\n\n"
        f"Мы напомним вам за 24 часа и за 2 часа до визита.\n"
        f"Ждём вас! 🚗"
    )
    await message.answer(confirmation, parse_mode="Markdown", reply_markup=main_menu_keyboard())
    
    # Notify owner if they have a chat_id
    if company.telegram_chat_id:
        try:
            await message.bot.send_message(
                company.telegram_chat_id,
                f"🔔 *Новая запись!*\n"
                f"Клиент: {message.from_user.full_name}\n"
                f"Услуга: {data.get('service_name')}\n"
                f"Время: {scheduled_at.strftime('%d.%m.%Y %H:%M')}\n"
                f"Телефон: {phone}",
                parse_mode="Markdown"
            )
        except Exception:
            pass
    
    await state.clear()


@router.message(F.text == "📞 Контакты")
async def show_contacts(message: Message, company: Company):
    text = f"📍 *{company.name}*\n\n"
    if company.address:
        text += f"📌 Адрес: {company.address}\n"
    if company.phone:
        text += f"📞 Телефон: {company.phone}\n"
    await message.answer(text, parse_mode="Markdown", reply_markup=main_menu_keyboard())


@router.message()
async def handle_text(message: Message, company: Company, db_session: AsyncSession):
    """Main AI handler for all other messages."""
    if not company:
        return
    
    checker = SubscriptionChecker(db_session)
    
    # Save incoming message
    client = await get_or_create_client(db_session, company, message)
    await save_message(db_session, company, client, message.text, MessageDirection.INCOMING)
    
    # Check subscription
    if not await checker.is_active(company.id):
        await message.answer("Сервис временно недоступен. Позвоните нам напрямую.")
        return
    
    # Check dialog limit for AI
    has_ai = await checker.has_feature(company.id, "has_ai")
    
    if has_ai:
        if not await checker.can_use_dialog(company.id):
            sub = await checker.get_subscription(company.id)
            await message.answer(checker.get_upgrade_message(sub.plan.name if sub else "start"))
            return
    
    # Get services for context
    svc_repo = ServiceRepository(db_session)
    services = await svc_repo.get_company_services(company.id)
    
    # Get recent messages for conversation context
    from app.domain.models.message import Message as Msg, MessageDirection as MD
    from sqlalchemy import select
    history_result = await db_session.execute(
        select(Msg).where(
            Msg.company_id == company.id,
            Msg.telegram_id == str(message.from_user.id),
        ).order_by(Msg.created_at.desc()).limit(10)
    )
    history_msgs = list(reversed(history_result.scalars().all()))
    conversation = [
        {
            "role": "user" if m.direction == MD.INCOMING else "assistant",
            "content": m.text
        }
        for m in history_msgs[:-1]  # Exclude the last (current) message
    ]
    
    # Working hours string
    from app.domain.models.company import WorkingHours
    from sqlalchemy.orm import selectinload
    result = await db_session.execute(
        select(Company).options(selectinload(Company.working_hours)).where(Company.id == company.id)
    )
    company_full = result.scalar_one()
    
    days = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
    wh_lines = []
    for wh in sorted(company_full.working_hours, key=lambda x: x.day_of_week):
        if wh.is_working and wh.open_time:
            wh_lines.append(f"{days[wh.day_of_week]}: {wh.open_time.strftime('%H:%M')}-{wh.close_time.strftime('%H:%M')}")
        else:
            wh_lines.append(f"{days[wh.day_of_week]}: Выходной")
    working_hours_str = ", ".join(wh_lines) if wh_lines else "уточняйте по телефону"
    
    if has_ai:
        await message.bot.send_chat_action(message.chat.id, "typing")
        response = await ai_service.generate_response(
            company_name=company.name,
            company_info=company.description or "",
            services=services,
            working_hours_str=working_hours_str,
            phone=company.phone or "",
            conversation_history=conversation,
            user_message=message.text,
        )
        await checker.increment_dialog_count(company.id)
    else:
        # Basic response without AI
        response = (
            f"Здравствуйте! Я администратор {company.name}.\n\n"
            f"Вы можете:\n"
            f"📋 Посмотреть услуги\n"
            f"📅 Записаться на ремонт\n"
            f"📞 Позвонить нам: {company.phone or 'уточните номер'}\n\n"
            f"Используйте кнопки меню ниже."
        )
    
    await save_message(db_session, company, client, response, MessageDirection.OUTGOING, is_ai=has_ai)
    await message.answer(response, reply_markup=main_menu_keyboard())
