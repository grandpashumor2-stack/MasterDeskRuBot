"""
Создаёт демо-автосервис для @MasterDeskRuBot.
Запустить один раз после init_db.py:
  docker compose run --rm api python scripts/init_demo.py
"""
import asyncio
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from datetime import datetime, time, timedelta
from app.infrastructure.database.connection import AsyncSessionLocal
from app.domain.models.company import Company, WorkingHours
from app.domain.models.service import Service, ServicePrice, ServiceCategory, PriceType
from app.domain.models.subscription import Subscription, SubscriptionStatus, PlanName
from app.domain.repositories.subscription import PlanRepository
from app.core.config import settings


async def seed_demo():
    async with AsyncSessionLocal() as session:
        from sqlalchemy import select

        # Check if demo already exists
        result = await session.execute(
            select(Company).where(Company.slug == "masterdesk-demo")
        )
        if result.scalar_one_or_none():
            print("✅ Demo company already exists")
            return

        # Create demo company
        company = Company(
            name="Авторемонт на Ленина",
            slug="masterdesk-demo",
            telegram_bot_token=settings.BOT_TOKEN,
            phone="+7 (495) 000-00-00",
            address="ул. Ленина, 42, Москва",
            city="Москва",
            description="Профессиональный автосервис. Работаем с 2010 года. Гарантия на все виды работ.",
            is_active=True,
            ai_system_prompt=(
                "Ты администратор автосервиса 'Авторемонт на Ленина'. "
                "Всегда вежлив, предлагаешь записаться. "
                "Уточняй марку авто для точной цены."
            ),
        )
        session.add(company)
        await session.flush()

        # Working hours: Mon-Fri 9-19, Sat 10-16, Sun - выходной
        hours = []
        for day in range(5):   # Mon-Fri
            hours.append(WorkingHours(
                company_id=company.id, day_of_week=day, is_working=True,
                open_time=time(9, 0), close_time=time(19, 0)
            ))
        hours.append(WorkingHours(  # Sat
            company_id=company.id, day_of_week=5, is_working=True,
            open_time=time(10, 0), close_time=time(16, 0)
        ))
        hours.append(WorkingHours(  # Sun
            company_id=company.id, day_of_week=6, is_working=False
        ))
        session.add_all(hours)

        # Services
        services_data = [
            {
                "name": "Замена масла и фильтра",
                "category": ServiceCategory.MAINTENANCE,
                "duration_minutes": 30,
                "keywords": ["масло", "замена масла", "ТО", "техобслуживание", "oil"],
                "prices": {"type": "by_make", "makes": {
                    "Toyota": 1500, "Kia": 1500, "Hyundai": 1500,
                    "BMW": 2500, "Mercedes": 3000, "Audi": 2500,
                    "Volkswagen": 2000, "Lada": 1200, "Ford": 1800,
                }},
            },
            {
                "name": "Диагностика ходовой части",
                "category": ServiceCategory.DIAGNOSTICS,
                "duration_minutes": 45,
                "keywords": ["подвеска", "стук", "ходовая", "диагностика", "стучит"],
                "prices": {"type": "fixed", "price": 800},
            },
            {
                "name": "Регулировка развал-схождения",
                "category": ServiceCategory.SUSPENSION,
                "duration_minutes": 45,
                "keywords": ["развал", "схождение", "сход-развал", "тянет", "уводит", "руль"],
                "prices": {"type": "fixed", "price": 1200},
            },
            {
                "name": "Замена тормозных колодок",
                "category": ServiceCategory.BRAKES,
                "duration_minutes": 60,
                "keywords": ["тормоза", "колодки", "тормозные колодки", "скрипят тормоза"],
                "prices": {"type": "range", "min": 1500, "max": 3500},
            },
            {
                "name": "Компьютерная диагностика",
                "category": ServiceCategory.DIAGNOSTICS,
                "duration_minutes": 30,
                "keywords": ["диагностика", "ошибки", "check engine", "лампочка", "сканер"],
                "prices": {"type": "fixed", "price": 500},
            },
            {
                "name": "Замена тормозных дисков",
                "category": ServiceCategory.BRAKES,
                "duration_minutes": 90,
                "keywords": ["диски", "тормозные диски", "вибрация при торможении"],
                "prices": {"type": "range", "min": 3000, "max": 7000},
            },
            {
                "name": "Диагностика кондиционера",
                "category": ServiceCategory.AC,
                "duration_minutes": 30,
                "keywords": ["кондиционер", "климат", "не холодит", "кондей", "ac"],
                "prices": {"type": "fixed", "price": 600},
            },
            {
                "name": "Заправка кондиционера",
                "category": ServiceCategory.AC,
                "duration_minutes": 60,
                "keywords": ["заправка кондиционера", "фреон", "плохо охлаждает"],
                "prices": {"type": "fixed", "price": 2500},
            },
            {
                "name": "Замена свечей зажигания",
                "category": ServiceCategory.ENGINE,
                "duration_minutes": 45,
                "keywords": ["свечи", "троит", "плохо заводится", "дёргается"],
                "prices": {"type": "range", "min": 800, "max": 2000},
            },
            {
                "name": "Шиномонтаж (4 колеса)",
                "category": ServiceCategory.TIRES,
                "duration_minutes": 40,
                "keywords": ["шины", "резина", "шиномонтаж", "переобуть", "колёса"],
                "prices": {"type": "fixed", "price": 1200},
            },
        ]

        for i, svc_data in enumerate(services_data):
            svc = Service(
                company_id=company.id,
                name=svc_data["name"],
                category=svc_data["category"],
                duration_minutes=svc_data["duration_minutes"],
                keywords=svc_data["keywords"],
                sort_order=i,
                is_active=True,
            )
            session.add(svc)
            await session.flush()

            p_data = svc_data["prices"]
            if p_data["type"] == "fixed":
                price = ServicePrice(service_id=svc.id, price_type=PriceType.FIXED,
                                     fixed_price=p_data["price"], is_default=True)
            elif p_data["type"] == "range":
                price = ServicePrice(service_id=svc.id, price_type=PriceType.RANGE,
                                     price_min=p_data["min"], price_max=p_data["max"], is_default=True)
            elif p_data["type"] == "by_make":
                price = ServicePrice(service_id=svc.id, price_type=PriceType.BY_MAKE,
                                     prices_by_make=p_data["makes"], is_default=True)
            session.add(price)

        # BUSINESS plan subscription (so AI works in demo)
        plan_repo = PlanRepository(session)
        plan = await plan_repo.get_by_name(PlanName.BUSINESS)
        if plan:
            sub = Subscription(
                company_id=company.id,
                plan_id=plan.id,
                status=SubscriptionStatus.ACTIVE,
                current_period_start=datetime.utcnow(),
                current_period_end=datetime.utcnow() + timedelta(days=3650),  # 10 лет для демо
            )
            session.add(sub)

        await session.commit()

        print(f"✅ Demo company created!")
        print(f"   Компания: Авторемонт на Ленина")
        print(f"   Бот: @MasterDeskRuBot")
        print(f"   Услуг: {len(services_data)}")
        print(f"   Тариф: BUSINESS (демо, 10 лет)")
        print()
        print(f"👉 Запустите бота: https://t.me/MasterDeskRuBot")


if __name__ == "__main__":
    asyncio.run(seed_demo())
