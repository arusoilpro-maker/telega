from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def main_menu_keyboard():
    kb = [
        [KeyboardButton(text="🔧 Заказать ремонт")],
        [KeyboardButton(text="📋 Мои заказы")],
        [KeyboardButton(text="👤 Профиль")],
        [KeyboardButton(text="📞 Связаться с поддержкой")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)