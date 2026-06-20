from aiogram.fsm.state import State, StatesGroup


class BookingStates(StatesGroup):
    waiting_service = State()
    waiting_car_info = State()
    waiting_phone = State()
    waiting_time_slot = State()
    confirming = State()


class OwnerStates(StatesGroup):
    waiting_service_name = State()
    waiting_service_price = State()
    waiting_campaign_text = State()
