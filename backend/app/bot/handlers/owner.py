from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command

router = Router()

@router.message(Command("appointments"))
async def cmd_appointments(message: Message):
    await message.answer("📋 Список записей пуст.")

@router.message(Command("stats"))
async def cmd_stats(message: Message):
    await message.answer("📊 Статистика недоступна.")
