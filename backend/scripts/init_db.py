"""
Seed: создаёт тарифные планы и администратора платформы.

Анализ рынка 2025:
  АвтоДилер Онлайн — от 1 495 ₽/мес (без бота, без AI)
  Splus            — от 2 550 ₽/мес (без бота, без AI)
  РемОнлайн       — не работает в РФ
  Битрикс24        — от 2 490 ₽/мес (общая CRM, не для авто)

МастерДеск — единственный с Telegram-ботом + AI.
Позиционирование: дешевле Splus на входе, дороже на верхних тарифах за AI.
"""
import asyncio
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.infrastructure.database.connection import AsyncSessionLocal
from app.domain.models.subscription import Plan, PlanName
from app.domain.models.user import User, Role
from app.core.security import get_password_hash
from app.core.config import settings


PLANS = [
    {
        "name": PlanName.START,
        "display_name": "Старт",
        # Дешевле АвтоДилер (1495) — низкий порог входа
        "monthly_price": 1490,
        "yearly_price": 13410,   # -25%, = 1117₽/мес
        "limits": {
            "max_dialogs": 200,
            "max_employees": 1,
            "max_clients": 300,
            "max_campaigns": 0,
            "has_ai": False,
            "has_auto_booking": True,
            "has_campaigns": False,
            "has_analytics_advanced": False,
            "has_api": False,
            "has_white_label": False,
        },
        "description": "Telegram-бот, приём заявок, до 200 диалогов, напоминания, базовая аналитика",
    },
    {
        "name": PlanName.BUSINESS,
        "display_name": "Бизнес",
        # Дороже Splus (2550) — за AI и бот
        "monthly_price": 2990,
        "yearly_price": 26910,   # -25%, = 2242₽/мес
        "limits": {
            "max_dialogs": 1000,
            "max_employees": 3,
            "max_clients": 2000,
            "max_campaigns": 5,
            "has_ai": True,
            "has_auto_booking": True,
            "has_campaigns": True,
            "has_analytics_advanced": True,
            "has_api": False,
            "has_white_label": False,
        },
        "description": "Всё из Старт + AI-консультант, до 1000 диалогов, рассылки, возврат клиентов",
    },
    {
        "name": PlanName.PREMIUM,
        "display_name": "Премиум",
        # Премиум сегмент — нет аналогов на рынке
        "monthly_price": 5990,
        "yearly_price": 53910,   # -25%, = 4492₽/мес
        "limits": {
            "max_dialogs": -1,
            "max_employees": -1,
            "max_clients": -1,
            "max_campaigns": -1,
            "has_ai": True,
            "has_auto_booking": True,
            "has_campaigns": True,
            "has_analytics_advanced": True,
            "has_api": True,
            "has_white_label": True,
        },
        "description": "Всё из Бизнес + безлимит, несколько точек, API, White Label",
    },
]


async def seed():
    async with AsyncSessionLocal() as session:
        from sqlalchemy import select

        for plan_data in PLANS:
            result = await session.execute(select(Plan).where(Plan.name == plan_data["name"]))
            existing = result.scalar_one_or_none()
            if not existing:
                plan = Plan(**plan_data)
                session.add(plan)
                print(f"✅ Тариф создан: {plan_data['display_name']} — {plan_data['monthly_price']} ₽/мес")
            else:
                existing.limits = plan_data["limits"]
                existing.monthly_price = plan_data["monthly_price"]
                existing.yearly_price = plan_data["yearly_price"]
                existing.display_name = plan_data["display_name"]
                print(f"🔄 Тариф обновлён: {plan_data['display_name']} — {plan_data['monthly_price']} ₽/мес")

        result = await session.execute(select(User).where(User.email == settings.ADMIN_EMAIL))
        admin = result.scalar_one_or_none()
        if not admin:
            admin = User(
                email=settings.ADMIN_EMAIL,
                hashed_password=get_password_hash(settings.ADMIN_PASSWORD),
                full_name="Администратор МастерДеск",
                role=Role.PLATFORM_ADMIN,
                is_active=True,
            )
            session.add(admin)
            print(f"✅ Админ создан: {settings.ADMIN_EMAIL}")
        else:
            admin.hashed_password = get_password_hash(settings.ADMIN_PASSWORD)
            print(f"🔄 Пароль админа обновлён")

        await session.commit()

        print("\n" + "─"*45)
        print("✅ База данных инициализирована!")
        print()
        print("📊 Тарифы МастерДеск (анализ рынка 2025):")
        print("   Старт   — 1 490 ₽/мес  (vs АвтоДилер 1 495 ₽)")
        print("   Бизнес  — 2 990 ₽/мес  (vs Splus 2 550 ₽ + AI)")
        print("   Премиум — 5 990 ₽/мес  (нет аналогов на рынке)")
        print()
        print(f"🔑 Логин: {settings.ADMIN_EMAIL}")
        print(f"🔑 Пароль: {settings.ADMIN_PASSWORD}")


if __name__ == "__main__":
    asyncio.run(seed())
