"""
Main menu keyboards
"""
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from typing import Optional

def get_main_keyboard(role: str = 'client') -> ReplyKeyboardMarkup:
    """
    Get main menu keyboard based on user role
    """
    builder = ReplyKeyboardBuilder()
    
    # Common buttons for all
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
            KeyboardButton(text="⚙️ Управление услугами")
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

def get_master_keyboard() -> ReplyKeyboardMarkup:
    """
    Keyboard for master's personal area
    """
    builder = ReplyKeyboardBuilder()
    builder.row(
        KeyboardButton(text="📋 Новые заказы"),
        KeyboardButton(text="✅ Мои заказы")
    )
    builder.row(
        KeyboardButton(text="💰 Баланс"),
        KeyboardButton(text="📊 Статистика")
    )
    builder.row(
        KeyboardButton(text="⚙️ Настройки профиля"),
        KeyboardButton(text="📅 Календарь")
    )
    builder.row(
        KeyboardButton(text="◀️ Назад в главное меню")
    )
    return builder.as_markup(resize_keyboard=True)

def get_admin_keyboard() -> ReplyKeyboardMarkup:
    """
    Admin panel keyboard
    """
    builder = ReplyKeyboardBuilder()
    builder.row(
        KeyboardButton(text="👥 Управление пользователями"),
        KeyboardButton(text="✅ Верификация мастеров")
    )
    builder.row(
        KeyboardButton(text="📊 Общая аналитика"),
        KeyboardButton(text="💰 Финансы")
    )
    builder.row(
        KeyboardButton(text="⚙️ Настройки платформы"),
        KeyboardButton(text="📢 Рассылки")
    )
    builder.row(
        KeyboardButton(text="🤖 AI настройки"),
        KeyboardButton(text="📈 SEO аналитика")
    )
    builder.row(
        KeyboardButton(text="◀️ Назад в главное меню")
    )
    return builder.as_markup(resize_keyboard=True)

def get_cancel_keyboard() -> ReplyKeyboardMarkup:
    """
    Simple cancel keyboard
    """
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="❌ Отмена"))
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=True)