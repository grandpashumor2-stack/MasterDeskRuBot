from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from datetime import datetime, timedelta
import os

from app.infrastructure.database.connection import get_db

templates = Jinja2Templates(directory="app/web/templates")
web_router = APIRouter(tags=["web"])


def get_token_from_cookie(request: Request):
    return request.cookies.get("access_token")


async def get_current_web_user(request: Request, session: AsyncSession = Depends(get_db)):
    token = get_token_from_cookie(request)
    if not token:
        return None
    try:
        from app.core.security import SECRET_KEY, ALGORITHM
        from jose import jwt
        from app.domain.models.user import User
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        result = await session.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()
    except Exception:
        return None


@web_router.get("/", response_class=HTMLResponse)
async def index(request: Request, session: AsyncSession = Depends(get_db)):
    user = await get_current_web_user(request, session)
    if user:
        if user.role.value == "platform_admin":
            return RedirectResponse("/admin")
        return RedirectResponse("/dashboard")
    return templates.TemplateResponse("login.html", {"request": request})


@web_router.get("/login", response_class=HTMLResponse)
async def login_get(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@web_router.post("/login")
async def login_post(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    session: AsyncSession = Depends(get_db),
):
    from app.core.security import verify_password, create_access_token
    from app.domain.models.user import User
    
    result = await session.execute(select(User).where(User.email == username))
    user = result.scalar_one_or_none()
    
    if not user or not verify_password(password, user.hashed_password):
        return templates.TemplateResponse("login.html", {
            "request": request, "error": "Неверный email или пароль"
        })
    
    token = create_access_token({"sub": str(user.id), "role": user.role.value})
    redirect_url = "/admin" if user.role.value == "platform_admin" else "/dashboard"
    response = RedirectResponse(redirect_url, status_code=302)
    response.set_cookie("access_token", token, httponly=False, max_age=86400, samesite="lax")
    return response


@web_router.get("/logout")
async def logout():
    response = RedirectResponse("/", status_code=302)
    response.delete_cookie("access_token")
    return response


@web_router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request, session: AsyncSession = Depends(get_db)):
    from app.domain.models.marketing import PageEvent
    session.add(PageEvent(event_type="register_view"))
    await session.commit()
    return templates.TemplateResponse("register.html", {"request": request})


@web_router.get("/demo", response_class=HTMLResponse)
async def demo_page(request: Request, session: AsyncSession = Depends(get_db)):
    from app.domain.models.marketing import PageEvent
    session.add(PageEvent(event_type="demo_view"))
    await session.commit()
    return templates.TemplateResponse("demo.html", {"request": request})


# ─────────────────────────── OWNER DASHBOARD ───────────────────────────

@web_router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, session: AsyncSession = Depends(get_db)):
    user = await get_current_web_user(request, session)
    if not user:
        return RedirectResponse("/")
    
    from app.domain.models.appointment import Appointment, AppointmentStatus
    from app.domain.models.client import Client
    from app.domain.models.subscription import Subscription
    from sqlalchemy.orm import selectinload
    
    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    company_id = user.company_id

    today_count = (await session.execute(
        select(func.count()).where(and_(
            Appointment.company_id == company_id,
            Appointment.scheduled_at >= today_start,
        ))
    )).scalar()

    month_count = (await session.execute(
        select(func.count()).where(and_(
            Appointment.company_id == company_id,
            Appointment.created_at >= month_start,
        ))
    )).scalar()

    total_clients = (await session.execute(
        select(func.count()).where(Client.company_id == company_id)
    )).scalar()

    returning = (await session.execute(
        select(func.count()).where(and_(
            Client.company_id == company_id, Client.visit_count >= 2
        ))
    )).scalar()

    # Today's appointments
    today_apts_result = await session.execute(
        select(Appointment)
        .options(selectinload(Appointment.client), selectinload(Appointment.service))
        .where(and_(
            Appointment.company_id == company_id,
            Appointment.scheduled_at >= today_start,
            Appointment.scheduled_at < today_start + timedelta(days=1),
        ))
        .order_by(Appointment.scheduled_at)
    )
    today_apts = list(today_apts_result.scalars().all())

    # Subscription info
    sub_result = await session.execute(
        select(Subscription)
        .options(selectinload(Subscription.plan))
        .where(Subscription.company_id == company_id)
    )
    sub = sub_result.scalar_one_or_none()

    from app.domain.models.company import Company
    company = await session.get(Company, company_id)

    return templates.TemplateResponse("owner/dashboard.html", {
        "request": request,
        "user": user,
        "company": company,
        "today_count": today_count,
        "month_count": month_count,
        "total_clients": total_clients,
        "returning_clients": returning,
        "today_appointments": today_apts,
        "subscription": sub,
        "now": now,
    })


@web_router.get("/clients", response_class=HTMLResponse)
async def clients_page(request: Request, session: AsyncSession = Depends(get_db)):
    user = await get_current_web_user(request, session)
    if not user:
        return RedirectResponse("/")
    from app.domain.models.client import Client
    from sqlalchemy.orm import selectinload
    result = await session.execute(
        select(Client)
        .where(Client.company_id == user.company_id)
        .options(selectinload(Client.vehicles))
        .order_by(Client.created_at.desc())
        .limit(200)
    )
    clients = list(result.scalars().all())
    return templates.TemplateResponse("owner/clients.html", {
        "request": request, "user": user, "clients": clients
    })


@web_router.get("/appointments", response_class=HTMLResponse)
async def appointments_page(request: Request, session: AsyncSession = Depends(get_db)):
    user = await get_current_web_user(request, session)
    if not user:
        return RedirectResponse("/")
    from app.domain.models.appointment import Appointment
    from sqlalchemy.orm import selectinload
    now = datetime.utcnow()
    result = await session.execute(
        select(Appointment)
        .where(Appointment.company_id == user.company_id)
        .options(
            selectinload(Appointment.client),
            selectinload(Appointment.service),
            selectinload(Appointment.employee),
        )
        .order_by(Appointment.scheduled_at.desc())
        .limit(100)
    )
    appointments = list(result.scalars().all())
    return templates.TemplateResponse("owner/appointments.html", {
        "request": request, "user": user, "appointments": appointments, "now": now,
        "services": await __import__("app.domain.repositories.service", fromlist=["ServiceRepository"]).ServiceRepository(session).get_company_services(user.company_id)
    })


@web_router.get("/services-page", response_class=HTMLResponse)
async def services_page(request: Request, session: AsyncSession = Depends(get_db)):
    user = await get_current_web_user(request, session)
    if not user:
        return RedirectResponse("/")
    from app.domain.models.service import Service
    from sqlalchemy.orm import selectinload
    result = await session.execute(
        select(Service)
        .where(Service.company_id == user.company_id)
        .options(selectinload(Service.prices))
        .order_by(Service.sort_order, Service.name)
    )
    services = list(result.scalars().all())
    return templates.TemplateResponse("owner/services.html", {
        "request": request, "user": user, "services": services
    })


@web_router.get("/campaigns-page", response_class=HTMLResponse)
async def campaigns_page(request: Request, session: AsyncSession = Depends(get_db)):
    user = await get_current_web_user(request, session)
    if not user:
        return RedirectResponse("/")
    from app.domain.models.campaign import Campaign
    result = await session.execute(
        select(Campaign)
        .where(Campaign.company_id == user.company_id)
        .order_by(Campaign.created_at.desc())
    )
    campaigns = list(result.scalars().all())
    return templates.TemplateResponse("owner/campaigns.html", {
        "request": request, "user": user, "campaigns": campaigns
    })


@web_router.get("/analytics-page", response_class=HTMLResponse)
async def analytics_page(request: Request, session: AsyncSession = Depends(get_db)):
    user = await get_current_web_user(request, session)
    if not user:
        return RedirectResponse("/")
    from app.domain.models.appointment import Appointment, AppointmentStatus
    from app.domain.models.client import Client
    from app.domain.models.service import Service
    from sqlalchemy import desc

    company_id = user.company_id
    now = datetime.utcnow()
    month_start = now.replace(day=1, hour=0, minute=0, second=0)

    # Monthly stats for chart (last 6 months)
    monthly_data = []
    for i in range(5, -1, -1):
        m_start = (now.replace(day=1) - timedelta(days=i * 30)).replace(day=1, hour=0, minute=0, second=0)
        m_end = (m_start + timedelta(days=32)).replace(day=1)
        count = (await session.execute(
            select(func.count()).where(and_(
                Appointment.company_id == company_id,
                Appointment.created_at >= m_start,
                Appointment.created_at < m_end,
            ))
        )).scalar()
        monthly_data.append({"month": m_start.strftime("%b"), "count": count})

    # Top services
    top_svc = await session.execute(
        select(Service.name, func.count(Appointment.id).label("cnt"))
        .join(Appointment, Appointment.service_id == Service.id, isouter=True)
        .where(Service.company_id == company_id)
        .group_by(Service.name)
        .order_by(desc("cnt"))
        .limit(5)
    )
    top_services = [{"name": r[0], "count": r[1]} for r in top_svc]

    total_clients = (await session.execute(
        select(func.count()).where(Client.company_id == company_id)
    )).scalar()

    returning = (await session.execute(
        select(func.count()).where(and_(
            Client.company_id == company_id, Client.visit_count >= 2
        ))
    )).scalar()

    from app.domain.models.message import Message
    total_msgs = (await session.execute(
        select(func.count()).where(Message.company_id == company_id)
    )).scalar()

    month_apts = (await session.execute(
        select(func.count()).where(and_(
            Appointment.company_id == company_id,
            Appointment.created_at >= month_start,
        ))
    )).scalar()

    conversion = round(month_apts / max(total_msgs, 1) * 100, 1)

    return templates.TemplateResponse("owner/analytics.html", {
        "request": request,
        "user": user,
        "monthly_data": monthly_data,
        "top_services": top_services,
        "total_clients": total_clients,
        "returning_clients": returning,
        "conversion_rate": conversion,
        "month_appointments": month_apts,
    })


@web_router.get("/settings-page", response_class=HTMLResponse)
async def settings_page(request: Request, session: AsyncSession = Depends(get_db)):
    user = await get_current_web_user(request, session)
    if not user:
        return RedirectResponse("/")
    from app.domain.models.company import Company, WorkingHours
    from sqlalchemy.orm import selectinload
    result = await session.execute(
        select(Company)
        .options(selectinload(Company.working_hours))
        .where(Company.id == user.company_id)
    )
    company = result.scalar_one_or_none()
    days = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
    wh_map = {wh.day_of_week: wh for wh in (company.working_hours if company else [])}
    return templates.TemplateResponse("owner/settings.html", {
        "request": request, "user": user, "company": company,
        "working_hours": wh_map, "days": days
    })


# ─────────────────────────── PLATFORM ADMIN ────────────────────────────

@web_router.get("/admin", response_class=HTMLResponse)
async def admin_dashboard(request: Request, session: AsyncSession = Depends(get_db)):
    user = await get_current_web_user(request, session)
    if not user or user.role.value != "platform_admin":
        return RedirectResponse("/")

    from app.domain.models.company import Company
    from app.domain.models.subscription import Subscription, SubscriptionStatus
    from sqlalchemy.orm import selectinload

    total_companies = (await session.execute(select(func.count()).select_from(Company))).scalar()

    active_subs = (await session.execute(
        select(func.count()).where(Subscription.status == SubscriptionStatus.ACTIVE)
    )).scalar()

    trial_subs = (await session.execute(
        select(func.count()).where(Subscription.status == SubscriptionStatus.TRIAL)
    )).scalar()

    from app.domain.repositories.subscription import SubscriptionRepository
    sub_repo = SubscriptionRepository(session)
    mrr = await sub_repo.get_mrr()

    month_ago = datetime.utcnow() - timedelta(days=30)
    churned = (await session.execute(
        select(func.count()).where(and_(
            Subscription.status == SubscriptionStatus.CANCELLED,
            Subscription.updated_at >= month_ago,
        ))
    )).scalar()

    # Recent companies
    recent_result = await session.execute(
        select(Company)
        .options(selectinload(Company.subscription).selectinload(Subscription.plan))
        .order_by(Company.created_at.desc())
        .limit(20)
    )
    recent_companies = list(recent_result.scalars().all())

    return templates.TemplateResponse("admin/dashboard.html", {
        "request": request,
        "user": user,
        "total_companies": total_companies,
        "active_subscriptions": active_subs,
        "trial_subscriptions": trial_subs,
        "mrr": round(mrr, 0),
        "arr": round(mrr * 12, 0),
        "churned": churned,
        "recent_companies": recent_companies,
    })


@web_router.get("/admin/companies", response_class=HTMLResponse)
async def admin_companies(request: Request, session: AsyncSession = Depends(get_db)):
    user = await get_current_web_user(request, session)
    if not user or user.role.value != "platform_admin":
        return RedirectResponse("/")

    from app.domain.models.company import Company
    from sqlalchemy.orm import selectinload
    result = await session.execute(
        select(Company)
        .options(selectinload(Company.subscription).selectinload(Subscription.plan))
        .order_by(Company.created_at.desc())
    )
    companies = list(result.scalars().all())
    from app.domain.models.subscription import Plan
    plans_result = await session.execute(select(Plan).where(Plan.is_active == True))
    plans = list(plans_result.scalars().all())

    # Считаем клиентов для каждой компании
    from app.domain.models.client import Client
    client_counts = {}
    for c in companies:
        count = (await session.execute(
            select(func.count()).where(Client.company_id == c.id)
        )).scalar()
        client_counts[str(c.id)] = count

    return templates.TemplateResponse("admin/companies.html", {
        "request": request, "user": user, "companies": companies, "plans": plans, "client_counts": client_counts
    })


from app.domain.models.subscription import Subscription

@web_router.get("/billing", response_class=HTMLResponse)
async def billing_page(request: Request, session: AsyncSession = Depends(get_db)):
    user = await get_current_web_user(request, session)
    if not user:
        return RedirectResponse("/")
    from app.domain.models.subscription import Subscription
    from sqlalchemy.orm import selectinload
    sub_result = await session.execute(
        select(Subscription)
        .options(selectinload(Subscription.plan))
        .where(Subscription.company_id == user.company_id)
    )
    sub = sub_result.scalar_one_or_none()
    return templates.TemplateResponse("owner/billing.html", {
        "request": request, "user": user, "subscription": sub
    })
