from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from app.bot.states.client import BookingState

router = Router()

@router.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer(
        f"👋 Добро пожаловать в МастерДеск!\n\n"
        f"Я помогу вам записаться на обслуживание.\n"
        f"Напишите /book чтобы начать запись."
    )

@router.message(F.text == "/book")
async def cmd_book(message: Message, state: FSMContext):
    await state.set_state(BookingState.waiting_for_name)
    await message.answer("Введите ваше имя:")

@router.message(BookingState.waiting_for_name)
async def process_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await state.set_state(BookingState.waiting_for_phone)
    await message.answer("Введите ваш номер телефона:")

@router.message(BookingState.waiting_for_phone)
async def process_phone(message: Message, state: FSMContext):
    await state.update_data(phone=message.text)
    data = await state.get_data()
    await state.clear()
    await message.answer(
        f"✅ Заявка принята!\n"
        f"Имя: {data['name']}\n"
        f"Телефон: {data['phone']}\n\n"
        f"Мы свяжемся с вами для подтверждения."
    )
