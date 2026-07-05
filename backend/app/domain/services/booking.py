from datetime import datetime, date, timedelta, time
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.domain.models.company import WorkingHours
from app.domain.repositories.appointment import AppointmentRepository
import uuid


class BookingService:
    def __init__(self, session: AsyncSession):
        self.apt_repo = AppointmentRepository(session)

    def _get_working_hours(self, working_hours: list[WorkingHours], target_date: date) -> Optional[WorkingHours]:
        day_of_week = target_date.weekday()  # 0=Mon, 6=Sun
        for wh in working_hours:
            if wh.day_of_week == day_of_week:
                return wh
        return None

    def _generate_slots(self, wh: WorkingHours, duration_minutes: int = 60) -> List[time]:
        """Generate available time slots for a working day."""
        if not wh.is_working or not wh.open_time or not wh.close_time:
            return []
        
        slots = []
        current = datetime.combine(date.today(), wh.open_time)
        end = datetime.combine(date.today(), wh.close_time)
        slot_delta = timedelta(minutes=duration_minutes)

        while current + slot_delta <= end:
            # Skip break time
            if wh.break_start and wh.break_end:
                break_s = datetime.combine(date.today(), wh.break_start)
                break_e = datetime.combine(date.today(), wh.break_end)
                if not (current >= break_s and current < break_e):
                    slots.append(current.time())
            else:
                slots.append(current.time())
            current += slot_delta

        return slots

    async def get_available_slots(
        self,
        company_id: uuid.UUID,
        working_hours: list[WorkingHours],
        days_ahead: int = 3,
        duration_minutes: int = 60,
    ) -> dict[date, List[time]]:
        """Get available booking slots for next N days."""
        available = {}
        today = (datetime.utcnow() + timedelta(hours=3)).date()  # МСК
        busy_slots: dict[date, List[datetime]] = {}

        for i in range(days_ahead):
            check_date = today + timedelta(days=i)
            busy = await self.apt_repo.get_busy_slots(company_id, check_date)
            busy_slots[check_date] = busy

        for i in range(days_ahead):
            check_date = today + timedelta(days=i)
            wh = self._get_working_hours(working_hours, check_date)
            if not wh or not wh.is_working:
                continue

            all_slots = self._generate_slots(wh, duration_minutes)
            busy_times = {dt.time() for dt in busy_slots.get(check_date, [])}
            free_slots = [s for s in all_slots if s not in busy_times]

            # Skip past time for today
            if check_date == today:
                msk_now = datetime.utcnow() + timedelta(hours=3)  # МСК
                # Add 1 hour buffer
                buffer = (msk_now + timedelta(hours=1)).time()
                free_slots = [s for s in free_slots if s > buffer]

            if free_slots:
                available[check_date] = free_slots

        return available

    def format_slots_message(self, slots: dict[date, List[time]]) -> str:
        """Format available slots as a readable message."""
        if not slots:
            return "К сожалению, свободных мест нет на ближайшие дни. Позвоните нам для записи."

        DAY_NAMES = {
            0: "Понедельник", 1: "Вторник", 2: "Среда",
            3: "Четверг", 4: "Пятница", 5: "Суббота", 6: "Воскресенье"
        }
        today = (datetime.utcnow() + timedelta(hours=3)).date()  # МСК
        lines = ["📅 Доступное время для записи:\n"]
        for d, times in list(slots.items())[:3]:  # Show max 3 days
            if d == today:
                day_label = "Сегодня"
            elif d == today + timedelta(days=1):
                day_label = "Завтра"
            else:
                day_label = f"{DAY_NAMES[d.weekday()]}, {d.strftime('%d.%m')}"

            time_strs = [t.strftime("%H:%M") for t in times[:5]]  # Max 5 slots per day
            lines.append(f"*{day_label}:* {', '.join(time_strs)}")

        lines.append("\nВыберите удобное время или напишите желаемое.")
        return "\n".join(lines)
