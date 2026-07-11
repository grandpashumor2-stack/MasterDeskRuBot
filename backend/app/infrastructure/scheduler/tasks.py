import asyncio
from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from app.core.config import settings

scheduler = AsyncIOScheduler(timezone=settings.SCHEDULER_TIMEZONE)


async def send_reminders():
    from app.infrastructure.database.connection import AsyncSessionLocal
    from app.domain.repositories.appointment import AppointmentRepository
    from app.domain.models.company import Company
    from aiogram import Bot

    async with AsyncSessionLocal() as session:
        apt_repo = AppointmentRepository(session)
        appointments = await apt_repo.get_pending_reminders()

        for apt in appointments:
            if not apt.client or not apt.client.telegram_id:
                continue
            company = await session.get(Company, apt.company_id)
            if not company:
                continue
            token = company.telegram_bot_token or settings.BOT_TOKEN
            if not token:
                continue
            try:
                bot = Bot(token=token)
                now = datetime.utcnow() + timedelta(hours=3)  # scheduled_at хранится как московское время
                hours_until = (apt.scheduled_at - now).total_seconds() / 3600

                if 23.83 <= hours_until <= 24.17 and not apt.reminder_24h_sent:
                    text = (
                        f"⏰ *Напоминание о записи*\n\n"
                        f"Завтра в *{apt.scheduled_at.strftime('%H:%M')}* "
                        f"вас ждут в {company.name}"
                    )
                    if apt.service:
                        text += f"\n🔧 {apt.service.name}"
                    text += f"\n📍 {company.address or ''}"
                    await bot.send_message(apt.client.telegram_id, text, parse_mode="Markdown")
                    apt.reminder_24h_sent = True

                elif 1.83 <= hours_until <= 2.17 and not apt.reminder_2h_sent:
                    text = (
                        f"🔔 *Через 2 часа!*\n\n"
                        f"Сегодня в *{apt.scheduled_at.strftime('%H:%M')}* "
                        f"ждём вас в {company.name}"
                    )
                    if apt.service:
                        text += f"\n🔧 {apt.service.name}"
                    if company.phone:
                        text += f"\n📞 {company.phone}"
                    await bot.send_message(apt.client.telegram_id, text, parse_mode="Markdown")
                    apt.reminder_2h_sent = True

                await bot.session.close()
            except Exception as e:
                print(f"Reminder error: {e}")

        await session.commit()


async def send_return_campaigns():
    from app.infrastructure.database.connection import AsyncSessionLocal
    from app.domain.repositories.company import CompanyRepository
    from app.domain.repositories.client import ClientRepository
    from aiogram import Bot

    async with AsyncSessionLocal() as session:
        company_repo = CompanyRepository(session)
        client_repo = ClientRepository(session)
        companies = await company_repo.get_active_companies()

        for company in companies:
            token = company.telegram_bot_token or settings.BOT_TOKEN
            if not token:
                continue
            clients = await client_repo.get_clients_for_return_campaign(company.id, days_since_visit=180)
            if not clients:
                continue
            try:
                bot = Bot(token=token)
                for client in clients[:10]:
                    text = (
                        f"👋 Здравствуйте, {client.full_name or 'дорогой клиент'}!\n\n"
                        f"Прошло 6 месяцев с вашего последнего визита в {company.name}.\n\n"
                        f"🔧 Пора на плановое ТО?\n\n"
                        f"Напишите нам или нажмите /start чтобы записаться."
                    )
                    try:
                        await bot.send_message(client.telegram_id, text)
                        await asyncio.sleep(0.1)
                    except Exception:
                        pass
                await bot.session.close()
            except Exception as e:
                print(f"Return campaign error: {e}")


async def check_expired_subscriptions():
    from app.infrastructure.database.connection import AsyncSessionLocal
    from app.domain.repositories.subscription import SubscriptionRepository
    from app.domain.models.subscription import Subscription, SubscriptionStatus
    from sqlalchemy import select, and_

    async with AsyncSessionLocal() as session:
        sub_repo = SubscriptionRepository(session)
        expired_trials = await sub_repo.get_expired_trials()
        for sub in expired_trials:
            sub.status = SubscriptionStatus.EXPIRED

        result = await session.execute(
            select(Subscription).where(
                and_(
                    Subscription.status == SubscriptionStatus.ACTIVE,
                    Subscription.current_period_end <= datetime.utcnow(),
                )
            )
        )
        for sub in result.scalars().all():
            sub.status = SubscriptionStatus.PAST_DUE

        await session.commit()


async def reset_monthly_dialog_counts():
    from app.infrastructure.database.connection import AsyncSessionLocal
    from app.domain.models.subscription import Subscription
    from sqlalchemy import update

    async with AsyncSessionLocal() as session:
        await session.execute(update(Subscription).values(dialogs_used=0))
        await session.commit()
        print("Счётчики диалогов сброшены.")


async def check_expiring_subscriptions():
    """Notify company owners 2 days before their subscription/trial ends."""
    from app.infrastructure.database.connection import AsyncSessionLocal
    from app.domain.models.subscription import Subscription, SubscriptionStatus
    from app.domain.models.company import Company
    from sqlalchemy import select, and_, or_
    from aiogram import Bot

    async with AsyncSessionLocal() as session:
        now = datetime.utcnow()
        window_start = now + timedelta(hours=44)
        window_end = now + timedelta(hours=52)

        result = await session.execute(
            select(Subscription).where(
                and_(
                    Subscription.expiry_notified == False,
                    Subscription.status.in_([SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIAL]),
                    or_(
                        and_(
                            Subscription.status == SubscriptionStatus.ACTIVE,
                            Subscription.current_period_end.between(window_start, window_end),
                        ),
                        and_(
                            Subscription.status == SubscriptionStatus.TRIAL,
                            Subscription.trial_ends_at.between(window_start, window_end),
                        ),
                    ),
                )
            )
        )
        subs = list(result.scalars().all())

        for sub in subs:
            company = await session.get(Company, sub.company_id)
            if not company or not company.telegram_chat_id:
                continue

            token = company.telegram_bot_token or settings.BOT_TOKEN
            if not token:
                continue

            end_date = sub.current_period_end if sub.status == SubscriptionStatus.ACTIVE else sub.trial_ends_at
            kind = "пробный период" if sub.status == SubscriptionStatus.TRIAL else "подписка"

            text = (
                f"Внимание! Ваш(а) {kind} заканчивается {end_date.strftime('%d.%m.%Y')}.\n\n"
                f"Чтобы не потерять доступ к MasterDesk, продлите подписку в личном кабинете."
            )

            try:
                bot = Bot(token=token)
                await bot.send_message(company.telegram_chat_id, text)
                await bot.session.close()
                sub.expiry_notified = True
            except Exception as e:
                print(f"Expiry notify error: {e}")

        await session.commit()


async def check_pending_payments():
    """Poll YooKassa for status of PENDING payments.

    We don't have HTTPS webhook configured yet (no domain/SSL), so instead
    of waiting for YooKassa to notify us, we periodically ask YooKassa
    directly: 'is this payment done yet?' and activate the subscription
    ourselves if so. Reuses the exact same activation logic as the webhook
    would have used (_on_success), just triggered differently.
    """
    from app.infrastructure.database.connection import AsyncSessionLocal
    from app.domain.models.subscription import Payment, PaymentStatus
    from app.api.v1.endpoints.payments import _on_success, _on_fail
    from sqlalchemy import select
    import httpx

    if not settings.YOOKASSA_SECRET_KEY:
        return

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Payment).where(Payment.status == PaymentStatus.PENDING)
        )
        pending = list(result.scalars().all())

    if not pending:
        return

    async with httpx.AsyncClient() as client:
        for payment in pending:
            try:
                r = await client.get(
                    f"https://api.yookassa.ru/v3/payments/{payment.external_id}",
                    auth=(settings.YOOKASSA_SHOP_ID, settings.YOOKASSA_SECRET_KEY),
                    timeout=15,
                )
                if r.status_code != 200:
                    continue
                obj = r.json()
                if obj.get("status") == "succeeded":
                    await _on_success(obj)
                elif obj.get("status") == "canceled":
                    await _on_fail(obj)
            except Exception as e:
                print(f"Payment poll error: {e}")


def setup_scheduler():
    scheduler.add_job(send_reminders, "interval", minutes=5, id="reminders")
    scheduler.add_job(
        send_return_campaigns,
        CronTrigger(day_of_week="mon", hour=10, minute=0),
        id="return_campaigns"
    )
    scheduler.add_job(check_expired_subscriptions, "interval", hours=1, id="check_subs")
    scheduler.add_job(check_expiring_subscriptions, "interval", hours=6, id="check_expiring")
    scheduler.add_job(check_pending_payments, "interval", minutes=20, id="check_payments")
    scheduler.add_job(
        reset_monthly_dialog_counts,
        CronTrigger(day=1, hour=0, minute=5),
        id="reset_dialogs"
    )
    scheduler.start()
    return scheduler
