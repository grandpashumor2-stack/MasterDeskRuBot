from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from datetime import date, time
from typing import List


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📋 Наши услуги"), KeyboardButton(text="💰 Цены")],
            [KeyboardButton(text="📅 Записаться"), KeyboardButton(text="📞 Контакты")],
        ],
        resize_keyboard=True,
    )


def services_keyboard(services: list) -> InlineKeyboardMarkup:
    buttons = []
    for svc in services:
        buttons.append([InlineKeyboardButton(
            text=f"{svc.name}",
            callback_data=f"book_service:{svc.id}"
        )])
    buttons.append([InlineKeyboardButton(text="↩️ Назад", callback_data="back_main")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def time_slots_keyboard(slots: dict[date, List[time]]) -> InlineKeyboardMarkup:
    buttons = []
    today = date.today()
    from datetime import timedelta

    DAY_LABELS = {0: "Пн", 1: "Вт", 2: "Ср", 3: "Чт", 4: "Пт", 5: "Сб", 6: "Вс"}
    
    for d, times in list(slots.items())[:3]:
        if d == today:
            day_label = "Сегодня"
        elif d == today + timedelta(days=1):
            day_label = "Завтра"
        else:
            day_label = f"{DAY_LABELS[d.weekday()]} {d.strftime('%d.%m')}"

        row = []
        for t in times[:4]:  # 4 slots per row max
            row.append(InlineKeyboardButton(
                text=f"{t.strftime('%H:%M')}",
                callback_data=f"slot:{d.isoformat()}:{t.strftime('%H:%M')}"
            ))
        if row:
            # Header button (not clickable, just label) - split into rows of 2
            buttons.append([InlineKeyboardButton(text=f"📅 {day_label}", callback_data="noop")])
            for i in range(0, len(row), 2):
                buttons.append(row[i:i+2])
    
    buttons.append([InlineKeyboardButton(text="↩️ Другое время", callback_data="other_time")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def confirm_booking_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Подтвердить", callback_data="confirm_booking"),
            InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_booking"),
        ]
    ])


def share_phone_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📱 Поделиться номером", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )
