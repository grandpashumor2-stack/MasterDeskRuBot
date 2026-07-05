from datetime import datetime
from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery, Contact, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.states.booking import BookingStates
from app.bot.keyboards.client import (
    main_menu_keyboard, services_keyboard,
    time_slots_keyboard, confirm_booking_keyboard, share_phone_keyboard,
    calendar_keyboard, day_time_slots_keyboard
)
from app.domain.models.company import Company
from app.domain.models.appointment import AppointmentSource
from app.domain.models.message import MessageDirection
from app.domain.repositories.client import ClientRepository
from app.domain.repositories.service import ServiceRepository
from app.domain.repositories.company import CompanyRepository
from app.domain.repositories.appointment import AppointmentRepository
from app.domain.services.booking import BookingService
from app.domain.services.subscription_checker import SubscriptionChecker
from app.infrastructure.ai import service as ai_service

router = Router()


def platform_main_keyboard():
    """Главное меню платформенного бота."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="🏢 Я владелец автосервиса",
                url="http://217.12.37.18/register"
            )
        ],
        [
            InlineKeyboardButton(
                text="ℹ️ О платформе МастерДеск",
                callback_data="about_platform"
            )
        ]
    ])


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
async def cmd_start(message: Message, state: FSMContext, company: Company, db_session: AsyncSession):
    if not company:
        # Проверяем deep link параметр (/start masterdesk1)
        args = message.text.split()[1] if message.text and len(message.text.split()) > 1 else None
        if args:
            from app.domain.repositories.company import CompanyRepository
            repo = CompanyRepository(db_session)
            found = await repo.get_by_slug(args.lower())
            if found:
                await state.clear()
                await state.update_data(company_slug=args.lower())
                client = await get_or_create_client(db_session, found, message)
                welcome = (
                    f"👋 Добро пожаловать в *{found.name}*!\n\n"
                    f"Я — ваш виртуальный администратор. Помогу:\n"
                    f"• Узнать цены на услуги\n"
                    f"• Записаться на ремонт\n"
                    f"• Ответить на вопросы\n\n"
                    f"Выберите действие или напишите ваш вопрос ⬇️"
                )
                await message.answer(welcome, reply_markup=main_menu_keyboard(), parse_mode="Markdown")
                return
        await state.clear()
        await message.answer(
            "👋 Добро пожаловать в *МастерДеск*!\n\n"
            "Для начала работы используйте ссылку от вашего автосервиса.\n"
            "Или введите код автосервиса:",
            parse_mode="Markdown",
            reply_markup=platform_main_keyboard()
        )
        await state.set_state(BookingStates.waiting_company_code)
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


@router.callback_query(F.data == "about_platform")
async def about_platform(callback: CallbackQuery):
    text = (
        "🚀 *МастерДеск* — платформа для автоматизации автосервисов\n\n"
        "Что умеет система:\n"
        "• 🤖 ИИ-администратор отвечает клиентам 24/7\n"
        "• 📅 Онлайн-запись прямо в Telegram\n"
        "• 📊 Аналитика и CRM для владельца\n"
        "• 📱 Рассылки и напоминания клиентам\n\n"
        "💼 Хотите подключить свой автосервис?\n"
        "Нажмите кнопку \"Я владелец\" и зарегистрируйтесь!"
    )
    await callback.message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_start")]
        ])
    )
    await callback.answer()


@router.callback_query(F.data == "back_to_start")
async def back_to_start(callback: CallbackQuery):
    text = (
        "👋 Добро пожаловать в *МастерДеск*!\n\n"
        "🚀 Платформа для автоматизации автосервисов\n\n"
        "Кто вы?"
    )
    await callback.message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=platform_main_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data == "client_search")
async def client_search(callback: CallbackQuery, db_session: AsyncSession):
    from app.domain.repositories.company import CompanyRepository
    repo = CompanyRepository(db_session)
    companies = await repo.get_active_companies()
    if not companies:
        await callback.message.edit_text(
            "🔧 Пока нет зарегистрированных автосервисов.\n\nПопробуйте позже.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_start")]
            ])
        )
        await callback.answer()
        return
    if len(companies) == 1:
        company = companies[0]
        client = await get_or_create_client(db_session, company, callback.message)
        welcome = (
            f"🔧 Добро пожаловать в *{company.name}*!\n\n"
            f"Я — ваш виртуальный администратор. Помогу:\n"
            f"• Узнать цены на услуги\n"
            f"• Записаться на ремонт\n"
            f"• Ответить на вопросы\n\n"
            f"Выберите действие или напишите ваш вопрос 👇"
        )
        await callback.message.answer(welcome, reply_markup=main_menu_keyboard(), parse_mode="Markdown")
        await callback.answer()
        return
    text = (
        "🔧 *Выберите автосервис:*\n\n"
        + "\n".join([f"• *{c.name}*" + (f" — {c.city}" if c.city else "") for c in companies])
        + "\n\nНапишите название сервиса или слово *список*"
    )
    await callback.message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_start")]
        ])
    )
    await callback.answer()


@router.message(F.text.lower() == "список")
async def list_companies(message: Message, db_session: AsyncSession):
    repo = CompanyRepository(db_session)
    companies = await repo.get_active_companies()
    if not companies:
        await message.answer("Пока нет зарегистрированных автосервисов.")
        return
    text = "🔧 *Доступные автосервисы:*\n\n"
    for c in companies:
        text += f"• *{c.name}*"
        if c.city:
            text += f" — {c.city}"
        if c.address:
            text += f", {c.address}"
        text += "\n"
    text += "\nОбратитесь напрямую к боту вашего автосервиса."
    await message.answer(text, parse_mode="Markdown")


@router.message(BookingStates.waiting_company_code)
async def company_code_received(message: Message, state: FSMContext, db_session: AsyncSession):
    code = message.text.strip().lower()
    from app.domain.repositories.company import CompanyRepository
    repo = CompanyRepository(db_session)
    company = await repo.get_by_slug(code)
    if not company:
        await message.answer(
            "❌ Автосервис с таким кодом не найден.\n"
            "Проверьте код и попробуйте ещё раз.\n\n"
            "Код выглядит так: *masterdesk1*",
            parse_mode="Markdown"
        )
        return
    await state.update_data(company_slug=code)
    client = await get_or_create_client(db_session, company, message)
    welcome = (
        f"✅ Вы выбрали *{company.name}*!\n\n"
        f"Я — ваш виртуальный администратор.\n"
        f"Выберите действие или напишите ваш вопрос ⬇️"
    )
    await state.clear()
    await message.answer(welcome, reply_markup=main_menu_keyboard(), parse_mode="Markdown")

@router.message(F.text == "🏠 Главное меню")
async def go_home(message: Message, state: FSMContext, company: Company):
    await state.clear()
    if not company:
        await message.answer("Выберите действие:", reply_markup=platform_main_keyboard())
        return
    welcome = (
        f"🔧 Добро пожаловать в *{company.name}*!\n\n"
        f"Я — ваш виртуальный администратор.\n"
        f"Выберите действие или напишите ваш вопрос 👇"
    )
    await message.answer(welcome, parse_mode="Markdown", reply_markup=main_menu_keyboard())

@router.message(F.text == "📋 Наши услуги")
async def show_services(message: Message, company: Company, db_session: AsyncSession):
    if not company:
        await message.answer("Используйте кнопки меню.", reply_markup=platform_main_keyboard())
        return
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



@router.message(F.text == "💰 Цены")
async def show_prices(message: Message, company: Company, db_session: AsyncSession):
    if not company:
        await message.answer("Используйте кнопки меню.", reply_markup=platform_main_keyboard())
        return
    svc_repo = ServiceRepository(db_session)
    services = await svc_repo.get_company_services(company.id)
    if not services:
        await message.answer("Прайс-лист пока не добавлен. Свяжитесь с нами напрямую.")
        return
    from app.domain.models.service import PriceType
    text = f"💰 *Прайс-лист {company.name}:*\n\n"
    for svc in services:
        text += f"• *{svc.name}*"
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
    text += "\n📅 Записаться на ремонт — нажмите *Записаться*"
    await message.answer(text, parse_mode="Markdown")

@router.message(F.text == "📅 Записаться")
async def start_booking(message: Message, state: FSMContext, company: Company, db_session: AsyncSession):
    if not company:
        await message.answer("Используйте кнопки меню.", reply_markup=platform_main_keyboard())
        return
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
            f"К сожалению, свободных мест нет на ближайшие дни.\n"
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


@router.callback_query(F.data == "other_time", BookingStates.waiting_time_slot)
async def other_time_requested(callback: CallbackQuery, state: FSMContext):
    from datetime import date as _date, timedelta
    today = (datetime.utcnow() + timedelta(hours=3)).date()  # МСК
    await callback.message.edit_text(
        "📅 Выберите дату из календаря:",
        reply_markup=calendar_keyboard(today.year, today.month, min_date=today)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("calnav:"), BookingStates.waiting_time_slot)
async def calendar_navigate(callback: CallbackQuery):
    from datetime import date as _date, timedelta
    _, ym = callback.data.split(":")
    year_str, month_str = ym.split("-")
    year, month = int(year_str), int(month_str)
    today = (datetime.utcnow() + timedelta(hours=3)).date()  # МСК
    await callback.message.edit_text(
        "📅 Выберите дату из календаря:",
        reply_markup=calendar_keyboard(year, month, min_date=today)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("calday:"), BookingStates.waiting_time_slot)
async def calendar_day_selected(callback: CallbackQuery, state: FSMContext, company: Company, db_session: AsyncSession):
    from datetime import date as _date, timedelta
    from sqlalchemy.orm import selectinload
    from sqlalchemy import select as _select

    _, date_str = callback.data.split(":")
    target_date = _date.fromisoformat(date_str)

    result = await db_session.execute(
        _select(Company).options(selectinload(Company.working_hours)).where(Company.id == company.id)
    )
    company_with_wh = result.scalar_one_or_none()

    data = await state.get_data()
    duration = data.get("duration", 60)

    booking_svc = BookingService(db_session)
    days_ahead = (target_date - (datetime.utcnow() + timedelta(hours=3)).date()).days + 1  # МСК
    if days_ahead < 1:
        days_ahead = 1
    all_slots = await booking_svc.get_available_slots(
        company.id,
        company_with_wh.working_hours if company_with_wh else [],
        days_ahead=days_ahead,
        duration_minutes=duration,
    )
    times = all_slots.get(target_date, [])

    if not times:
        await callback.message.edit_text(
            f"К сожалению, на {target_date.strftime('%d.%m.%Y')} свободных мест нет.\nВыберите другую дату:",
            reply_markup=calendar_keyboard(target_date.year, target_date.month, min_date=(datetime.utcnow() + timedelta(hours=3)).date())
        )
        await callback.answer()
        return

    await callback.message.edit_text(
        f"📅 Свободное время на {target_date.strftime('%d.%m.%Y')}:",
        reply_markup=day_time_slots_keyboard(target_date, times, target_date.year, target_date.month)
    )
    await callback.answer()


@router.callback_query(F.data == "cal_back_to_slots", BookingStates.waiting_time_slot)
async def cal_back_to_slots(callback: CallbackQuery, state: FSMContext, company: Company, db_session: AsyncSession):
    from sqlalchemy.orm import selectinload
    from sqlalchemy import select as _select

    result = await db_session.execute(
        _select(Company).options(selectinload(Company.working_hours)).where(Company.id == company.id)
    )
    company_with_wh = result.scalar_one_or_none()

    data = await state.get_data()
    duration = data.get("duration", 60)

    booking_svc = BookingService(db_session)
    slots = await booking_svc.get_available_slots(
        company.id, company_with_wh.working_hours if company_with_wh else [], duration_minutes=duration
    )

    if not slots:
        await callback.message.edit_text(
            f"К сожалению, свободных мест нет на ближайшие дни.\nПозвоните нам: {company.phone or 'номер не указан'}"
        )
        await state.clear()
        await callback.answer()
        return

    msg_text = booking_svc.format_slots_message(slots)
    await callback.message.edit_text(msg_text, reply_markup=time_slots_keyboard(slots), parse_mode="Markdown")
    await callback.answer()


@router.callback_query(F.data == "noop")
async def noop_callback(callback: CallbackQuery):
    await callback.answer()


@router.message(F.contact, BookingStates.waiting_phone)
async def phone_received(message: Message, state: FSMContext, company: Company, db_session: AsyncSession):
    phone = message.contact.phone_number
    await _create_appointment(message, state, company, db_session, phone)


@router.message(BookingStates.waiting_phone)
async def phone_text_received(message: Message, state: FSMContext, company: Company, db_session: AsyncSession):
    phone = message.text.strip()
    if not any(c.isdigit() for c in phone):
        await message.answer("Пожалуйста, введите номер телефона или нажмите кнопку.")
        return
    await _create_appointment(message, state, company, db_session, phone)


async def _create_appointment(message: Message, state: FSMContext, company: Company, db_session: AsyncSession, phone: str):
    data = await state.get_data()
    client = await get_or_create_client(db_session, company, message)
    client.phone = phone
    client.visit_count = (client.visit_count or 0) + 1
    client.last_visit_at = datetime.utcnow()

    apt_repo = AppointmentRepository(db_session)

    dt_str = f"{data['selected_date']} {data['selected_time']}"
    scheduled_at = datetime.strptime(dt_str if ":" in dt_str else dt_str + ":00", "%Y-%m-%d %H:%M")

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
    # Сохраняем автомобиль клиента
    car_info = data.get('car_info', '')
    if car_info and client:
        from app.domain.models.client import Vehicle
        parts = car_info.split()
        year = next((int(p) for p in parts if p.isdigit() and len(p)==4), None)
        make = parts[0] if parts else None
        model = ' '.join(parts[1:-1]) if year and len(parts)>2 else ' '.join(parts[1:]) if len(parts)>1 else None
        db_session.add(Vehicle(client_id=client.id, make=make, model=model, year=year))
        await db_session.commit()
    appointment = appointment  # already created

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
    await message.answer(confirmation, reply_markup=main_menu_keyboard())

    if company.telegram_chat_id:
        try:
            name = message.from_user.full_name.replace("_", " ")
            svc = str(data.get("service_name", "")).replace("_", " ")
            dt = scheduled_at.strftime("%d.%m.%Y %H:%M")
            txt = "Новая запись. Клиент: " + name + ". Услуга: " + svc + ". Время: " + dt + ". Тел: " + str(phone)
            await message.bot.send_message(company.telegram_chat_id, txt)
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Owner notify error: {e}")

    await state.clear()


@router.message(F.text == "📞 Контакты")
async def show_contacts(message: Message, company: Company):
    if not company:
        await message.answer("Используйте кнопки меню.", reply_markup=platform_main_keyboard())
        return
    text = f"📍 *{company.name}*\n\n"
    if company.address:
        text += f"📌 Адрес: {company.address}\n"
    if company.phone:
        text += f"📞 Телефон: {company.phone}\n"
    await message.answer(text, parse_mode="Markdown", reply_markup=main_menu_keyboard())


@router.message(F.text == "❓  Задать вопрос")
async def ask_question(message: Message, company: Company):
    if not company:
        await message.answer("Используйте кнопки меню.", reply_markup=platform_main_keyboard())
        return
    await message.answer(
        f"Здравствуйте! Я администратор {company.name}.\n\n"
        f"Вы можете:\n"
        f"📋 Посмотреть услуги\n"
        f"📅 Записаться на ремонт\n"
        f"📞 Позвонить нам: {company.phone or 'уточните номер'}\n\n"
        f"Используйте кнопки меню ниже."
    )

@router.message()
async def handle_text(message: Message, company: Company, db_session: AsyncSession):
    if not company:
        await message.answer(
            "👋 Выберите действие:",
            reply_markup=platform_main_keyboard()
        )
        return

    checker = SubscriptionChecker(db_session)
    client = await get_or_create_client(db_session, company, message)
    await save_message(db_session, company, client, message.text, MessageDirection.INCOMING)

    if not await checker.is_active(company.id):
        await message.answer("Сервис временно недоступен. Позвоните нам напрямую.")
        return

    has_ai = False  # AI disabled until ANTHROPIC_API_KEY is set

    if has_ai:
        if not await checker.can_use_dialog(company.id):
            sub = await checker.get_subscription(company.id)
            await message.answer(checker.get_upgrade_message(sub.plan.name if sub else "start"))
            return

    svc_repo = ServiceRepository(db_session)
    services = await svc_repo.get_company_services(company.id)

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
        {"role": "user" if m.direction == MD.INCOMING else "assistant", "content": m.text}
        for m in history_msgs[:-1]
    ]

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
