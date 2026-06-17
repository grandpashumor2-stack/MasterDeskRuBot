"""Background scheduler tasks: reminders, return campaigns, subscription checks."""
import asyncio
from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from aiogram import Bot

from app.core.config import settings
from app.infrastructure.database.connection import AsyncSessionLocal
from app.domain.repositories.appointment import AppointmentRepository
from app.domain.repositories.company import CompanyRepository
from app.domain.repositories.client import ClientRepository
from app.domain.repositories.subscription import SubscriptionRepository
from app.domain.models.subscription import SubscriptionStatus
from app.domain.models.appointment import AppointmentStatus


scheduler = AsyncIOScheduler(timezone=settings.SCHEDULER_TIMEZONE)


async def send_reminders():
    """Send appointment reminders: 24h and 2h before."""
    async with AsyncSessionLocal() as session:
        apt_repo = AppointmentRepository(session)
        appointments = await apt_repo.get_pending_reminders()
        
        for apt in appointments:
            if not apt.client or not apt.client.telegram_id:
                continue
            
            company = await session.get(
                __import__("app.domain.models.company", fromlist=["Company"]).Company,
                apt.company_id
            )
            if not company or not company.telegram_bot_token:
                continue
            
            try:
                bot = Bot(token=company.telegram_bot_token)
                now = datetime.utcnow()
                hours_until = (apt.scheduled_at - now).total_seconds() / 3600
                
                if 22 <= hours_until <= 26 and not apt.reminder_24h_sent:
                    text = (
                        f"⏰ *Напоминание о записи*\n\n"
                        f"Завтра в *{apt.scheduled_at.strftime('%H:%M')}* у вас запись в {company.name}"
                    )
                    if apt.service:
                        text += f"\n🔧 Услуга: {apt.service.name}"
                    if apt.car_description:
                        text += f"\n🚗 Автомобиль: {apt.car_description}"
                    text += f"\n\nАдрес: {company.address or 'уточните по телефону'}"
                    
                    await bot.send_message(apt.client.telegram_id, text, parse_mode="Markdown")
                    apt.reminder_24h_sent = True
                
                elif 1.4 <= hours_until <= 2.6 and not apt.reminder_2h_sent:
                    text = (
                        f"🔔 *Напоминание — через 2 часа!*\n\n"
                        f"Сегодня в *{apt.scheduled_at.strftime('%H:%M')}* вас ждут в {company.name}"
                    )
                    if apt.service:
                        text += f"\n🔧 {apt.service.name}"
                    text += f"\n\n📍 {company.address or ''}"
                    if company.phone:
                        text += f"\n📞 {company.phone}"
                    
                    await bot.send_message(apt.client.telegram_id, text, parse_mode="Markdown")
                    apt.reminder_2h_sent = True
                
                await bot.session.close()
            except Exception as e:
                print(f"Reminder error for apt {apt.id}: {e}")
        
        await session.commit()


async def send_return_campaigns():
    """Send return campaigns to clients who haven't visited in a while."""
    async with AsyncSessionLocal() as session:
        company_repo = CompanyRepository(session)
        client_repo = ClientRepository(session)
        companies = await company_repo.get_active_companies()
        
        for company in companies:
            if not company.telegram_bot_token:
                continue
            
            # Get clients who haven't visited in 6 months
            clients_to_return = await client_repo.get_clients_for_return_campaign(
                company.id, days_since_visit=180
            )
            
            if not clients_to_return:
                continue
            
            try:
                bot = Bot(token=company.telegram_bot_token)
                for client in clients_to_return[:10]:  # Max 10 per run to avoid spam
                    text = (
                        f"👋 Здравствуйте, {client.full_name or 'дорогой клиент'}!\n\n"
                        f"Уже прошло 6 месяцев с вашего последнего визита в {company.name}.\n\n"
                        f"🔧 Пришло время планового ТО?\n\n"
                        f"Запишитесь сейчас и получите консультацию мастера бесплатно.\n\n"
                        f"📅 Нажмите /start чтобы записаться."
                    )
                    try:
                        await bot.send_message(client.telegram_id, text)
                        await asyncio.sleep(0.1)  # Rate limiting
                    except Exception:
                        pass
                await bot.session.close()
            except Exception as e:
                print(f"Return campaign error for company {company.id}: {e}")


async def check_expired_subscriptions():
    """Mark expired trial and subscription periods."""
    async with AsyncSessionLocal() as session:
        sub_repo = SubscriptionRepository(session)
        
        # Expire trials
        expired_trials = await sub_repo.get_expired_trials()
        for sub in expired_trials:
            sub.status = SubscriptionStatus.EXPIRED
        
        # Check active subscriptions past end date
        from sqlalchemy import select, and_
        from app.domain.models.subscription import Subscription
        result = await session.execute(
            select(Subscription).where(
                and_(
                    Subscription.status == SubscriptionStatus.ACTIVE,
                    Subscription.current_period_end <= datetime.utcnow(),
                )
            )
        )
        expired_subs = list(result.scalars().all())
        for sub in expired_subs:
            sub.status = SubscriptionStatus.PAST_DUE
        
        await session.commit()
        
        if expired_trials or expired_subs:
            print(f"Expired: {len(expired_trials)} trials, {len(expired_subs)} subscriptions")


async def reset_monthly_dialog_counts():
    """Reset dialog counters at start of each month."""
    async with AsyncSessionLocal() as session:
        from sqlalchemy import update
        from app.domain.models.subscription import Subscription
        await session.execute(update(Subscription).values(dialogs_used=0))
        await session.commit()
        print("Monthly dialog counters reset.")


def setup_scheduler():
    """Configure and start all scheduled tasks."""
    # Reminders every 15 minutes
    scheduler.add_job(send_reminders, "interval", minutes=15, id="reminders")
    
    # Return campaigns — once a week on Monday at 10:00
    scheduler.add_job(
        send_return_campaigns,
        CronTrigger(day_of_week="mon", hour=10, minute=0),
        id="return_campaigns"
    )
    
    # Check expired subscriptions — every hour
    scheduler.add_job(check_expired_subscriptions, "interval", hours=1, id="check_subs")
    
    # Reset dialog counters — 1st of each month at midnight
    scheduler.add_job(
        reset_monthly_dialog_counts,
        CronTrigger(day=1, hour=0, minute=5),
        id="reset_dialogs"
    )
    
    scheduler.start()
    return scheduler
