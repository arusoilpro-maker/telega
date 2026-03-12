"""
Reply keyboards for the bot
"""
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from typing import List, Optional

def get_main_keyboard(role: str = 'client') -> ReplyKeyboardMarkup:
    """Get main menu keyboard based on user role"""
    
    builder = ReplyKeyboardBuilder()
    
    # Common buttons for all users
    builder.row(
        KeyboardButton(text="🔧 Найти мастера"),
        KeyboardButton(text="📋 Мои заказы")
    )
    
    builder.row(
        KeyboardButton(text="📍 Карта мастеров"),
        KeyboardButton(text="💬 Поддержка")
    )
    
    # Role-specific buttons
    if role == 'master':
        builder.row(
            KeyboardButton(text="📊 Моя статистика"),
            KeyboardButton(text="⚙️ Управление")
        )
    elif role == 'admin':
        builder.row(
            KeyboardButton(text="👥 Пользователи"),
            KeyboardButton(text="📈 Аналитика"),
            KeyboardButton(text="⚙️ Админка")
        )
    else:  # client
        builder.row(
            KeyboardButton(text="⭐ Стать мастером"),
            KeyboardButton(text="⚙️ Настройки")
        )
    
    return builder.as_markup(resize_keyboard=True)

def get_phone_keyboard() -> ReplyKeyboardMarkup:
    """Get phone number request keyboard"""
    
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="📱 Отправить номер", request_contact=True))
    builder.add(KeyboardButton(text="◀️ Назад"))
    builder.adjust(1)
    
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=True)

def get_location_keyboard() -> ReplyKeyboardMarkup:
    """Get location request keyboard"""
    
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="📍 Отправить геопозицию", request_location=True))
    builder.add(KeyboardButton(text="🏙️ Выбрать город"))
    builder.add(KeyboardButton(text="◀️ Назад"))
    builder.adjust(1)
    
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=True)

def get_cancel_keyboard() -> ReplyKeyboardMarkup:
    """Get cancel keyboard"""
    
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="❌ Отмена"))
    
    return builder.as_markup(resize_keyboard=True)

def get_payment_keyboard() -> ReplyKeyboardMarkup:
    """Get payment methods keyboard"""
    
    builder = ReplyKeyboardBuilder()
    builder.row(
        KeyboardButton(text="💳 Карта онлайн"),
        KeyboardButton(text="📱 Apple Pay")
    )
    builder.row(
        KeyboardButton(text="💰 Наличные"),
        KeyboardButton(text="💸 Перевод")
    )
    builder.row(KeyboardButton(text="◀️ Назад"))
    
    return builder.as_markup(resize_keyboard=True)

def get_rating_keyboard() -> ReplyKeyboardMarkup:
    """Get rating keyboard"""
    
    builder = ReplyKeyboardBuilder()
    builder.row(
        KeyboardButton(text="⭐ 1"),
        KeyboardButton(text="⭐ 2"),
        KeyboardButton(text="⭐ 3")
    )
    builder.row(
        KeyboardButton(text="⭐ 4"),
        KeyboardButton(text="⭐ 5"),
        KeyboardButton(text="⏭ Пропустить")
    )
    
    return builder.as_markup(resize_keyboard=True)

def get_confirmation_keyboard() -> ReplyKeyboardMarkup:
    """Get confirmation keyboard"""
    
    builder = ReplyKeyboardBuilder()
    builder.row(
        KeyboardButton(text="✅ Подтвердить"),
        KeyboardButton(text="❌ Отмена")
    )
    
    return builder.as_markup(resize_keyboard=True)