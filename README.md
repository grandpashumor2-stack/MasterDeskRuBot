# 🚗 МастерДеск

SaaS-платформа для автосервисов России.
Telegram-бот + AI + веб-панель + ЮKassa.

## Тарифы (анализ рынка 2025)

| | START | BUSINESS | PREMIUM |
|--|-------|----------|---------|
| **Цена/мес** | **1 490 ₽** | **3 490 ₽** | **6 990 ₽** |
| Telegram бот | ✅ | ✅ | ✅ |
| AI-консультант | ❌ | ✅ | ✅ |
| Диалогов/мес | 300 | 2 000 | ∞ |
| Рассылки | ❌ | ✅ | ✅ |

## Запуск

```bash
cp backend/.env.example backend/.env
# Заполнить: ANTHROPIC_API_KEY, YOOKASSA_SECRET_KEY
cd backend && bash scripts/deploy.sh
```

Бот: @MasterDeskRuBot
