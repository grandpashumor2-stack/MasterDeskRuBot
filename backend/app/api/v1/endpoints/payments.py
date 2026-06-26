"""ЮKassa платежи. ShopID=1370046 берётся из .env"""
import uuid, json
from datetime import datetime, timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.core.security import get_current_owner
from app.infrastructure.database.connection import get_db
from app.domain.models.subscription import (
    Subscription, SubscriptionStatus, Payment, PaymentStatus,
    Invoice, Plan, PlanName
)
from app.domain.repositories.subscription import SubscriptionRepository, PlanRepository

router = APIRouter(prefix="/payments", tags=["payments"])
YOOKASSA_API = "https://api.yookassa.ru/v3"


async def _yk_create(amount: Decimal, desc: str, return_url: str, meta: dict) -> dict:
    import httpx
    if not settings.YOOKASSA_SECRET_KEY:
        raise HTTPException(400, "Задайте YOOKASSA_SECRET_KEY в .env")
    async with httpx.AsyncClient() as c:
        r = await c.post(
            f"{YOOKASSA_API}/payments",
            json={
                "amount": {"value": f"{amount:.2f}", "currency": "RUB"},
                "confirmation": {"type": "redirect", "return_url": return_url},
                "capture": True, "description": desc, "metadata": meta,
            },
            auth=(settings.YOOKASSA_SHOP_ID, settings.YOOKASSA_SECRET_KEY),
            headers={"Idempotence-Key": str(uuid.uuid4())},
            timeout=15,
        )
    if r.status_code != 200:
        raise HTTPException(502, f"ЮKassa error: {r.text}")
    return r.json()


class CreatePaymentRequest(BaseModel):
    plan_name: PlanName
    is_yearly: bool = False
    return_url: str = "https://masterdesk.ru/billing?payment=success"


@router.get("/plans")
async def get_plans(session: AsyncSession = Depends(get_db)):
    repo = PlanRepository(session)
    plans = await repo.get_active_plans()
    return [{"id": str(p.id), "name": p.name.value, "display_name": p.display_name,
             "monthly_price": float(p.monthly_price), "yearly_price": float(p.yearly_price),
             "yearly_discount_pct": round((1 - float(p.yearly_price)/(float(p.monthly_price)*12))*100),
             "limits": p.limits, "description": p.description} for p in plans]


@router.post("/create")
async def create_payment(
    data: CreatePaymentRequest,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_owner),
):
    plan = await PlanRepository(session).get_by_name(data.plan_name)
    if not plan:
        raise HTTPException(404, "Тариф не найден")

    amount = plan.yearly_price if data.is_yearly else plan.monthly_price
    period = "год" if data.is_yearly else "месяц"
    desc   = f"МастерДеск — {plan.display_name} на {period}"
    meta   = {"company_id": str(current_user.company_id), "plan_id": str(plan.id),
              "plan_name": plan.name.value, "is_yearly": str(data.is_yearly)}

    yk = await _yk_create(amount, desc, data.return_url, meta)

    # Сохранить pending-платёж
    sub_repo = SubscriptionRepository(session)
    sub = await sub_repo.get_by_company(current_user.company_id)
    if not sub:
        sub = Subscription(company_id=current_user.company_id, plan_id=plan.id,
                           status=SubscriptionStatus.TRIAL)
        session.add(sub)
        await session.flush()
    else:
        sub.plan_id = plan.id
        await session.flush()

    session.add(Payment(subscription_id=sub.id, amount=amount,
                        status=PaymentStatus.PENDING, payment_method="yookassa",
                        external_id=yk["id"]))
    await session.commit()

    return {"payment_id": yk["id"],
            "confirmation_url": yk["confirmation"]["confirmation_url"],
            "amount": float(amount), "description": desc}


@router.post("/webhook/yookassa")
async def webhook(request: Request, bg: BackgroundTasks,
                  session: AsyncSession = Depends(get_db)):
    """
    Настроить в ЮKassa:
    yookassa.ru → Интеграция → HTTP-уведомления
    URL: https://ВАШ_ДОМЕН/api/v1/payments/webhook/yookassa
    """
    body = await request.body()
    try:
        event = json.loads(body)
    except Exception:
        raise HTTPException(400, "Invalid JSON")

    obj, etype = event.get("object", {}), event.get("event", "")
    if etype == "payment.succeeded":
        bg.add_task(_on_success, obj)
    elif etype == "payment.canceled":
        bg.add_task(_on_fail, obj)
    return {"ok": True}


async def _on_success(obj: dict):
    from app.infrastructure.database.connection import AsyncSessionLocal
    from app.domain.models.company import Company
    meta    = obj.get("metadata", {})
    cid     = meta.get("company_id")
    pid     = meta.get("plan_id")
    yearly  = meta.get("is_yearly") == "True"
    amount  = Decimal(obj["amount"]["value"])
    days    = 365 if yearly else 30

    if not cid or not pid:
        return
    async with AsyncSessionLocal() as session:
        r = await session.execute(select(Payment).where(Payment.external_id == obj["id"]))
        p = r.scalar_one_or_none()
        if p:
            p.status = PaymentStatus.PAID

        sub_repo = SubscriptionRepository(session)
        sub = await sub_repo.get_by_company(uuid.UUID(cid))
        now = datetime.utcnow()
        if sub:
            start = sub.current_period_end or now
            sub.status = SubscriptionStatus.ACTIVE
            sub.plan_id = uuid.UUID(pid)
            sub.is_yearly = yearly
            sub.current_period_start = start
            sub.current_period_end = start + timedelta(days=days)
        else:
            sub = Subscription(company_id=uuid.UUID(cid), plan_id=uuid.UUID(pid),
                               status=SubscriptionStatus.ACTIVE, is_yearly=yearly,
                               current_period_start=now,
                               current_period_end=now + timedelta(days=days))
            session.add(sub)
            await session.flush()

        inv = f"MD-{now.strftime('%Y%m')}-{str(uuid.uuid4())[:6].upper()}"
        session.add(Invoice(subscription_id=sub.id, number=inv, amount=amount,
                            period_start=now, period_end=now+timedelta(days=days),
                            is_paid=True, paid_at=now))
        await session.commit()

        # Telegram-уведомление владельцу
        company = await session.get(Company, uuid.UUID(cid))
        plan    = await session.get(Plan, uuid.UUID(pid))
        if company and company.telegram_bot_token and company.telegram_chat_id:
            try:
                from aiogram import Bot
                bot = Bot(token=company.telegram_bot_token)
                await bot.send_message(
                    company.telegram_chat_id,
                    f"✅ *Оплата прошла!*\n\n"
                    f"Тариф: *{plan.display_name if plan else '—'}*\n"
                    f"Сумма: *{int(amount):,} ₽*".replace(",", " "),
                    parse_mode="Markdown")
                await bot.session.close()
            except Exception:
                pass


async def _on_fail(obj: dict):
    from app.infrastructure.database.connection import AsyncSessionLocal
    async with AsyncSessionLocal() as session:
        r = await session.execute(select(Payment).where(Payment.external_id == obj.get("id")))
        p = r.scalar_one_or_none()
        if p:
            p.status = PaymentStatus.FAILED
            await session.commit()


@router.get("/history")
async def history(session: AsyncSession = Depends(get_db),
                  current_user=Depends(get_current_owner)):
    sub = await SubscriptionRepository(session).get_by_company(current_user.company_id)
    if not sub:
        return []
    r = await session.execute(select(Payment).where(Payment.subscription_id == sub.id)
                              .order_by(Payment.created_at.desc()))
    return list(r.scalars().all())


@router.get("/invoices")
async def invoices(session: AsyncSession = Depends(get_db),
                   current_user=Depends(get_current_owner)):
    sub = await SubscriptionRepository(session).get_by_company(current_user.company_id)
    if not sub:
        return []
    r = await session.execute(select(Invoice).where(Invoice.subscription_id == sub.id)
                              .order_by(Invoice.created_at.desc()))
    return list(r.scalars().all())
