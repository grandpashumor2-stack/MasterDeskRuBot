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
def calendar_keyboard(year: int, month: int, min_date: date = None) -> InlineKeyboardMarkup:
    import calendar as pycal
    if min_date is None:
        min_date = date.today()
    MONTH_NAMES = {
        1: "Январь", 2: "Февраль", 3: "Март", 4: "Апрель", 5: "Май", 6: "Июнь",
        7: "Июль", 8: "Август", 9: "Сентябрь", 10: "Октябрь", 11: "Ноябрь", 12: "Декабрь"
    }
    cal = pycal.Calendar(firstweekday=0)
    month_days = cal.monthdayscalendar(year, month)

    buttons = []

    prev_month = month - 1 if month > 1 else 12
    prev_year = year if month > 1 else year - 1
    next_month = month + 1 if month < 12 else 1
    next_year = year if month < 12 else year + 1

    nav_row = []
    if (prev_year, prev_month) >= (min_date.year, min_date.month):
        nav_row.append(InlineKeyboardButton(text="◀️", callback_data=f"calnav:{prev_year}-{prev_month:02d}"))
    else:
        nav_row.append(InlineKeyboardButton(text=" ", callback_data="noop"))
    nav_row.append(InlineKeyboardButton(text=f"{MONTH_NAMES[month]} {year}", callback_data="noop"))
    nav_row.append(InlineKeyboardButton(text="▶️", callback_data=f"calnav:{next_year}-{next_month:02d}"))
    buttons.append(nav_row)

    buttons.append([InlineKeyboardButton(text=d, callback_data="noop") for d in ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]])

    for week in month_days:
        row = []
        for day_num in week:
            if day_num == 0:
                row.append(InlineKeyboardButton(text=" ", callback_data="noop"))
                continue
            d = date(year, month, day_num)
            if d < min_date:
                row.append(InlineKeyboardButton(text=" ", callback_data="noop"))
            else:
                row.append(InlineKeyboardButton(text=str(day_num), callback_data=f"calday:{d.isoformat()}"))
        buttons.append(row)

    buttons.append([InlineKeyboardButton(text="↩️ К списку слотов", callback_data="cal_back_to_slots")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def day_time_slots_keyboard(target_date: date, times: List[time], year: int, month: int) -> InlineKeyboardMarkup:
    buttons = []
    row = []
    for t in times:
        row.append(InlineKeyboardButton(
            text=t.strftime("%H:%M"),
            callback_data=f"slot:{target_date.isoformat()}:{t.strftime('%H:%M')}"
        ))
        if len(row) == 3:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    buttons.append([InlineKeyboardButton(text="◀️ К календарю", callback_data=f"calnav:{year}-{month:02d}")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)
