from datetime import datetime, timedelta
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from app.domain.models.company import Company
from app.domain.models.appointment import Appointment, AppointmentStatus
from app.domain.models.client import Client
from app.domain.models.subscription import Subscription, SubscriptionStatus
from app.domain.repositories.appointment import AppointmentRepository
from app.domain.repositories.service import ServiceRepository
from app.domain.repositories.client import ClientRepository
from app.domain.repositories.subscription import SubscriptionRepository

router = Router()


async def is_owner(message: Message, company: Company, db_session: AsyncSession) -> bool:
    """Check if the message sender is the company owner."""
    if not company:
        return False
    result = await db_session.execute(
        select(Company).where(Company.telegram_chat_id == str(message.from_user.id))
    )
    return result.scalar_one_or_none() is not None


@router.message(Command("today"))
async def cmd_today(message: Message, company: Company, db_session: AsyncSession):
    if not company:
        return
    
    apt_repo = AppointmentRepository(db_session)
    appointments = await apt_repo.get_today_appointments(company.id)
    
    if not appointments:
        await message.answer("📅 На сегодня записей нет.")
        return
    
    text = f"📅 *Записи на сегодня ({len(appointments)}):*\n\n"
    for apt in appointments:
        status_emoji = {"pending": "🟡", "confirmed": "✅", "in_progress": "🔧", "completed": "✔️", "cancelled": "❌"}.get(apt.status.value, "⚪")
        text += f"{status_emoji} *{apt.scheduled_at.strftime('%H:%M')}*"
        if apt.service:
            text += f" — {apt.service.name}"
        if apt.client_name:
            text += f"\n   👤 {apt.client_name}"
        if apt.client_phone:
            text += f" | 📞 {apt.client_phone}"
        if apt.car_description:
            text += f"\n   🚗 {apt.car_description}"
        text += "\n\n"
    
    await message.answer(text, parse_mode="Markdown")


@router.message(Command("stats"))
async def cmd_stats(message: Message, company: Company, db_session: AsyncSession):
    if not company:
        return
    
    now = datetime.utcnow()
    month_start = now.replace(day=1, hour=0, minute=0, second=0)
    
    # Appointments this month
    apt_result = await db_session.execute(
        select(func.count()).where(
            and_(
                Appointment.company_id == company.id,
                Appointment.created_at >= month_start,
            )
        )
    )
    monthly_appointments = apt_result.scalar()
    
    # Completed this month
    completed_result = await db_session.execute(
        select(func.count()).where(
            and_(
                Appointment.company_id == company.id,
                Appointment.status == AppointmentStatus.COMPLETED,
                Appointment.created_at >= month_start,
            )
        )
    )
    completed = completed_result.scalar()
    
    # Total clients
    client_result = await db_session.execute(
        select(func.count()).where(Client.company_id == company.id)
    )
    total_clients = client_result.scalar()
    
    # Returning clients (visited 2+ times)
    returning_result = await db_session.execute(
        select(func.count()).where(
            and_(Client.company_id == company.id, Client.visit_count >= 2)
        )
    )
    returning_clients = returning_result.scalar()
    
    # Subscription info
    sub_repo = SubscriptionRepository(db_session)
    sub = await sub_repo.get_by_company(company.id)
    
    text = f"📊 *Статистика {company.name}*\n\n"
    text += f"📅 Записей за месяц: {monthly_appointments}\n"
    text += f"✅ Выполнено: {completed}\n"
    
    if monthly_appointments > 0:
        conversion = round(completed / monthly_appointments * 100)
        text += f"📈 Конверсия: {conversion}%\n"
    
    text += f"\n👥 Всего клиентов: {total_clients}\n"
    text += f"🔄 Постоянных клиентов: {returning_clients}\n"
    
    if sub:
        status_map = {
            "trial": "🆓 Пробный период",
            "active": "✅ Активна",
            "past_due": "⚠️ Просрочена",
            "cancelled": "❌ Отменена",
            "expired": "⏱ Истекла",
        }
        text += f"\n💳 Подписка: {sub.plan.display_name if sub.plan else 'неизвестно'}\n"
        text += f"Статус: {status_map.get(sub.status.value, sub.status.value)}\n"
        if sub.status == SubscriptionStatus.TRIAL and sub.trial_ends_at:
            days_left = (sub.trial_ends_at - datetime.utcnow()).days
            text += f"Пробный период: {days_left} дн.\n"
        elif sub.current_period_end:
            text += f"Следующее списание: {sub.current_period_end.strftime('%d.%m.%Y')}\n"
        
        if sub.plan:
            max_dialogs = sub.plan.limits.get("max_dialogs", 0)
            if max_dialogs != -1:
                text += f"💬 Диалогов: {sub.dialogs_used}/{max_dialogs}\n"
            else:
                text += f"💬 Диалогов: {sub.dialogs_used} (без лимита)\n"
    
    await message.answer(text, parse_mode="Markdown")


@router.message(Command("appointments"))
async def cmd_appointments(message: Message, company: Company, db_session: AsyncSession):
    if not company:
        return
    
    apt_repo = AppointmentRepository(db_session)
    # Show upcoming confirmed appointments
    now = datetime.utcnow()
    week_later = now + timedelta(days=7)
    appointments = await apt_repo.get_company_appointments(
        company.id,
        status=AppointmentStatus.CONFIRMED,
        date_from=now,
        date_to=week_later,
    )
    
    if not appointments:
        await message.answer("📅 Нет предстоящих записей на ближайшую неделю.")
        return
    
    text = f"📅 *Предстоящие записи ({len(appointments)}):*\n\n"
    for apt in appointments:
        text += f"📌 *{apt.scheduled_at.strftime('%d.%m %H:%M')}*\n"
        if apt.service:
            text += f"   {apt.service.name}\n"
        if apt.client_name:
            text += f"   👤 {apt.client_name}"
        if apt.client_phone:
            text += f" | 📞 {apt.client_phone}"
        if apt.car_description:
            text += f"\n   🚗 {apt.car_description}"
        text += "\n\n"
    
    await message.answer(text, parse_mode="Markdown")


@router.message(Command("services"))
async def cmd_services(message: Message, company: Company, db_session: AsyncSession):
    if not company:
        return
    
    svc_repo = ServiceRepository(db_session)
    services = await svc_repo.get_company_services(company.id, active_only=False)
    
    if not services:
        await message.answer("Услуги не добавлены. Добавьте через веб-панель.")
        return
    
    text = f"🔧 *Ваши услуги:*\n\n"
    for svc in services:
        status = "✅" if svc.is_active else "❌"
        text += f"{status} *{svc.name}* ({svc.duration_minutes} мин)\n"
        if svc.prices:
            p = svc.prices[0]
            from app.domain.models.service import PriceType
            if p.price_type == PriceType.FIXED:
                text += f"   💰 {int(p.fixed_price):,} ₽\n".replace(",", " ")
            elif p.price_type == PriceType.RANGE:
                text += f"   💰 {int(p.price_min):,}—{int(p.price_max):,} ₽\n".replace(",", " ")
            elif p.price_type == PriceType.BY_MAKE:
                makes = ", ".join([f"{k}: {int(v):,}₽" for k, v in list(p.prices_by_make.items())[:3]])
                text += f"   💰 {makes}\n"
        text += "\n"
    
    text += "Управляйте услугами через веб-панель."
    await message.answer(text, parse_mode="Markdown")


@router.message(Command("leads"))
async def cmd_leads(message: Message, company: Company, db_session: AsyncSession):
    if not company:
        return
    
    # Show recent pending appointments as leads
    apt_repo = AppointmentRepository(db_session)
    appointments = await apt_repo.get_company_appointments(
        company.id, status=AppointmentStatus.PENDING
    )
    
    if not appointments:
        await message.answer("📩 Нет новых заявок.")
        return
    
    text = f"📩 *Новые заявки ({len(appointments)}):*\n\n"
    for apt in appointments[-10:]:  # Last 10
        text += f"🔔 *{apt.created_at.strftime('%d.%m %H:%M')}*\n"
        if apt.client_name:
            text += f"   👤 {apt.client_name}"
        if apt.client_phone:
            text += f" | 📞 {apt.client_phone}"
        if apt.service:
            text += f"\n   🔧 {apt.service.name}"
        if apt.car_description:
            text += f"\n   🚗 {apt.car_description}"
        text += "\n\n"
    
    await message.answer(text, parse_mode="Markdown")
