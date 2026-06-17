import json
import re
from typing import Optional
import anthropic
from app.core.config import settings
from app.domain.models.service import Service, ServicePrice, PriceType


client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)


INTENT_DETECTION_PROMPT = """Ты система распознавания намерений для автосервиса.

Проанализируй сообщение клиента и верни JSON:
{
  "intent": "price_inquiry|booking|status_check|greeting|complaint|other",
  "service_keywords": ["список ключевых слов услуги"],
  "car_make": "марка авто или null",
  "car_model": "модель авто или null",
  "urgency": "normal|urgent",
  "phone": "номер телефона или null"
}

Примеры маппинга:
- "стучит подвеска" → service_keywords: ["диагностика подвески"]
- "тянет вправо" → service_keywords: ["развал-схождение"]
- "кондиционер не холодит" → service_keywords: ["кондиционер"]
- "замена масла" → service_keywords: ["замена масла", "ТО"]
- "тормоза скрипят" → service_keywords: ["тормоза", "колодки"]
- "не заводится" → service_keywords: ["диагностика", "двигатель"]

Верни ТОЛЬКО JSON без пояснений."""


CHAT_SYSTEM_PROMPT = """Ты вежливый AI-администратор автосервиса "{company_name}".

О компании:
{company_info}

Правила:
1. Отвечай ТОЛЬКО на русском языке
2. Будь дружелюбным и профессиональным
3. НИКОГДА не придумывай цены — только из контекста
4. Если цена не найдена — предложи оставить заявку
5. Предлагай записаться на ремонт
6. Уточняй марку авто для точной цены
7. Отвечай кратко и по делу

Доступные услуги и цены:
{services_info}

Рабочие часы:
{working_hours}

Контакты: {phone}"""


async def detect_intent(message: str) -> dict:
    try:
        response = await client.messages.create(
            model=settings.AI_MODEL,
            max_tokens=300,
            messages=[{"role": "user", "content": f"{INTENT_DETECTION_PROMPT}\n\nСообщение: {message}"}]
        )
        text = response.content[0].text.strip()
        text = re.sub(r"```json\n?|\n?```", "", text).strip()
        return json.loads(text)
    except Exception:
        return {
            "intent": "other",
            "service_keywords": [],
            "car_make": None,
            "car_model": None,
            "urgency": "normal",
            "phone": None
        }


def build_services_info(services: list[Service]) -> str:
    lines = []
    for svc in services:
        if not svc.is_active:
            continue
        line = f"• {svc.name} ({svc.duration_minutes} мин)"
        if svc.prices:
            price = svc.prices[0]
            if price.price_type == PriceType.FIXED:
                line += f" — {int(price.fixed_price):,} ₽".replace(",", " ")
            elif price.price_type == PriceType.RANGE:
                line += f" — от {int(price.price_min):,} до {int(price.price_max):,} ₽".replace(",", " ")
            elif price.price_type == PriceType.BY_MAKE:
                makes = ", ".join([f"{k}: {int(v):,} ₽".replace(",", " ") for k, v in price.prices_by_make.items()])
                line += f" — {makes}"
            elif price.price_type == PriceType.ON_REQUEST:
                line += " — по запросу"
        lines.append(line)
    return "\n".join(lines) if lines else "Услуги уточняются"


async def generate_response(
    company_name: str,
    company_info: str,
    services: list[Service],
    working_hours_str: str,
    phone: str,
    conversation_history: list[dict],
    user_message: str,
) -> str:
    services_info = build_services_info(services)
    system = CHAT_SYSTEM_PROMPT.format(
        company_name=company_name,
        company_info=company_info,
        services_info=services_info,
        working_hours=working_hours_str,
        phone=phone or "не указан",
    )
    messages = conversation_history[-10:]
    messages.append({"role": "user", "content": user_message})
    response = await client.messages.create(
        model=settings.AI_MODEL,
        max_tokens=500,
        system=system,
        messages=messages,
    )
    return response.content[0].text
