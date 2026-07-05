from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, EmailStr
from app.infrastructure.database.connection import get_db
from app.core.security import verify_password, create_access_token, get_password_hash
from app.domain.models.user import User, Role

router = APIRouter(prefix="/auth", tags=["auth"])

class UserRegister(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    company_name: str
    phone: str | None = None

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

@router.post("/login", response_model=TokenResponse)
async def login(form: OAuth2PasswordRequestForm = Depends(), session: AsyncSession = Depends(get_db)):
    result = await session.execute(select(User).where(User.email == form.username))
    user = result.scalar_one_or_none()
    if not user or not verify_password(form.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token({"sub": str(user.id), "role": user.role.value})
    return TokenResponse(access_token=token)

@router.post("/register")
async def register(data: UserRegister, session: AsyncSession = Depends(get_db)):
    result = await session.execute(select(User).where(User.email == data.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")
    from app.domain.models.company import Company
    from app.domain.repositories.company import CompanyRepository
    company_repo = CompanyRepository(session)
    counter = 1
    while True:
        slug = f"masterdesk{counter}"
        if not await company_repo.get_by_slug(slug):
            break
        counter += 1
    company = Company(
        name=data.company_name,
        slug=slug,
        phone=data.phone,
    )
    session.add(company)
    await session.flush()
    user = User(
        email=data.email,
        hashed_password=get_password_hash(data.password),
        full_name=data.full_name,
        role=Role.COMPANY_OWNER,
        company_id=company.id,
    )
    session.add(user)
    await session.flush()
    from app.domain.models.subscription import Subscription, SubscriptionStatus
    from app.domain.repositories.subscription import SubscriptionRepository, PlanRepository
    plan_repo = PlanRepository(session)
    plans = await plan_repo.get_active_plans()
    start_plan = next((p for p in plans if p.name.value == "start"), plans[0] if plans else None)
    if start_plan:
        from datetime import datetime, timedelta
        sub = Subscription(
            company_id=company.id,
            plan_id=start_plan.id,
            status=SubscriptionStatus.TRIAL,
            trial_ends_at=datetime.utcnow() + timedelta(days=7),
        )
        session.add(sub)
    await session.commit()
    try:
        from aiogram import Bot
        from app.core.config import settings
        if settings.BOT_TOKEN:
            notify_bot = Bot(token=settings.BOT_TOKEN)
            await notify_bot.send_message(
                6466766416,
                f"Новая регистрация автосервиса!\n\n"
                f"Название: {data.company_name}\n"
                f"Владелец: {data.full_name}\n"
                f"Email: {data.email}\n"
                f"Телефон: {data.phone or 'не указан'}\n"
                f"Код: {slug}"
            )
            await notify_bot.session.close()
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Registration notify error: {e}")

    token = create_access_token({"sub": str(user.id), "role": user.role.value})
    return {"access_token": token, "token_type": "bearer", "company_code": slug}
