from aiogram.fsm.state import State, StatesGroup

class OrderStates(StatesGroup):
    choosing_service = State()
    choosing_master = State()
    choosing_datetime = State()
    entering_address = State()
    confirming = State()