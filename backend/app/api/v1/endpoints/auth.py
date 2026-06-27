from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, EmailStr
from datetime import timedelta

from app.infrastructure.database.connection import get_db
from app.core.security import verify_password, create_access_token, get_password_hash
from app.domain.models.user import User, Role
from app.core.config import settings

router = APIRouter(prefix="/auth", tags=["auth"])


class UserRegister(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    company_name: str
    company_slug: str
    phone: str | None = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str


@router.post("/token", response_model=TokenResponse)
async def login(form: OAuth2PasswordRequestForm = Depends(), session: AsyncSession = Depends(get_db)):
    result = await session.execute(select(User).where(User.email == form.username))
    user = result.scalar_one_or_none()
    if not user or not verify_password(form.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password")
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    
    token = create_access_token({"sub": str(user.id), "role": user.role.value})
    return TokenResponse(access_token=token, role=user.role.value)


@router.post("/register")
async def register(data: UserRegister, session: AsyncSession = Depends(get_db)):
    """Register new company owner with 7-day trial."""
    # Check email unique
    result = await session.execute(select(User).where(User.email == data.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create company
    from app.domain.models.company import Company
    from app.domain.repositories.company import CompanyRepository
    company_repo = CompanyRepository(session)
    
    existing = await company_repo.get_by_slug(data.company_slug)
    if existing:
        raise HTTPException(status_code=400, detail="Company slug already taken")
    
    company = Company(
        name=data.company_name,
        slug=data.company_slug,
        phone=data.phone,
        telegram_bot_token="8743483767:AAE2mOWHN9og5Ahefplv6x_xeelk92FtaF8",
    )
    session.add(company)
    await session.flush()
    
    # Create user
    user = User(
        email=data.email,
        hashed_password=get_password_hash(data.password),
        full_name=data.full_name,
        role=Role.COMPANY_OWNER,
        company_id=company.id,
    )
    session.add(user)
    await session.flush()
    
    # Create trial subscription on START plan
    from app.domain.models.subscription import Subscription, SubscriptionStatus, Plan, PlanName
    from app.domain.repositories.subscription import PlanRepository
    from datetime import datetime
    
    plan_repo = PlanRepository(session)
    start_plan = await plan_repo.get_by_name(PlanName.START)
    if start_plan:
        sub = Subscription(
            company_id=company.id,
            plan_id=start_plan.id,
            status=SubscriptionStatus.TRIAL,
            trial_ends_at=datetime.utcnow() + timedelta(days=settings.TRIAL_DAYS),
        )
        session.add(sub)
    
    # Add default working hours Mon-Sat 9-19
    from app.domain.models.company import WorkingHours
    from datetime import time
    default_hours = [
        WorkingHours(company_id=company.id, day_of_week=i, is_working=True,
                     open_time=time(9, 0), close_time=time(19, 0))
        for i in range(6)  # Mon-Sat
    ]
    default_hours.append(
        WorkingHours(company_id=company.id, day_of_week=6, is_working=False)
    )
    session.add_all(default_hours)
    
    await session.commit()
    
    token = create_access_token({"sub": str(user.id), "role": user.role.value})
    return {
        "access_token": token,
        "token_type": "bearer",
        "company_id": str(company.id),
        "message": f"Добро пожаловать! Пробный период {settings.TRIAL_DAYS} дней активирован."
    }
