"""
Бот МастерДеск для мессенджера MAX.

Пока реализован только платформенный экран (продающий питч + кнопки
"Подключить" / "Демо" / "Тарифы") — тот же, что в Telegram-боте.
Полный флоу записи клиента на услугу для MAX будет добавлен отдельно.

Запуск: MAX_BOT_TOKEN=... python scripts/max_bot_manager.py
"""
import asyncio
import logging

from maxapi import Bot, Dispatcher
from maxapi.enums.parse_mode import TextFormat
from maxapi.filters.command import CommandStart
from maxapi.types.attachments.buttons.callback_button import CallbackButton
from maxapi.types.attachments.buttons.link_button import LinkButton
from maxapi.types.updates.bot_started import BotStarted
from maxapi.types.updates.message_callback import MessageCallback
from maxapi.types.updates.message_created import MessageCreated
from maxapi.utils.inline_keyboard import InlineKeyboardBuilder

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot()  # токен читается из переменной окружения MAX_BOT_TOKEN
dp = Dispatcher()

WELCOME_TEXT = (
    "👋 **Добро пожаловать в МастерДеск**\n\n"
    "Не теряйте клиентов вечером и в выходные — МастерДеск сам "
    "принимает заявки и записывает клиентов 24/7.\n\n"
    "Что вы получите:\n\n"
    "✅ Онлайн-запись клиентов\n"
    "✅ Управление услугами и ценами\n"
    "✅ Напоминания клиентам\n"
    "✅ Возврат клиентов на обслуживание\n"
    "✅ Подключение за 5 минут\n\n"
    "🎁 1 месяц бесплатно"
)

PRICING_TEXT = (
    "💰 **Тарифы МастерДеск**\n\n"
    "🚗 **Старт** — 1490 ₽/мес\n"
    "🔧 **Бизнес** — 2990 ₽/мес\n"
    "⭐ **Премиум** — 5990 ₽/мес\n\n"
    "🎁 Первый месяц — бесплатно на любом тарифе.\n"
    "Точный список функций каждого тарифа — на странице регистрации."
    "🔧 **Бизнес** — 2990 ₽/мес\n"
    "⭐ **Премиум** — 5990 ₽/мес\n\n"
    "🎁 Первый месяц — бесплатно на любом тарифе.\n"
    "Точный список функций каждого тарифа — на странице регистрации."
)

CB_PRICING = "pricing"
CB_BACK = "back_to_start"


def main_keyboard() -> InlineKeyboardBuilder:
    kb = InlineKeyboardBuilder()
    kb.row(LinkButton(text="🚗 Подключить автосервис", url="https://master-desk.ru/register"))
    kb.row(LinkButton(text="📹 Посмотреть демо", url="https://master-desk.ru/demo"))
    kb.row(CallbackButton(text="💰 Тарифы", payload=CB_PRICING))
    return kb


def pricing_keyboard() -> InlineKeyboardBuilder:
    kb = InlineKeyboardBuilder()
    kb.row(LinkButton(text="🚗 Подключить автосервис", url="https://master-desk.ru/register"))
    kb.row(CallbackButton(text="◀️ Назад", payload=CB_BACK))
    return kb


@dp.bot_started()
async def on_bot_started(event: BotStarted) -> None:
    """Пользователь впервые нажал «Начать» в диалоге с ботом."""
    await bot.send_message(
        user_id=event.user.user_id,
        text=WELCOME_TEXT,
        format=TextFormat.MARKDOWN,
        attachments=[main_keyboard().as_markup()],
    )


@dp.message_created(CommandStart())
async def on_start(event: MessageCreated) -> None:
    await event.message.answer(
        text=WELCOME_TEXT,
        format=TextFormat.MARKDOWN,
        attachments=[main_keyboard().as_markup()],
    )


@dp.message_callback()
async def on_callback(event: MessageCallback) -> None:
    payload = event.callback.payload if event.callback else None
    if event.message is None:
        await event.answer()
        return

    if payload == CB_PRICING:
        await event.edit(
            text=PRICING_TEXT,
            format=TextFormat.MARKDOWN,
            attachments=[pricing_keyboard().as_markup()],
        )
    elif payload == CB_BACK:
        await event.edit(
            text=WELCOME_TEXT,
            format=TextFormat.MARKDOWN,
            attachments=[main_keyboard().as_markup()],
        )

    await event.answer()


async def main() -> None:
    logger.info("Starting MAX bot (МастерДеск)...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
