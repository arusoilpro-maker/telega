"""
Inline keyboards for interactive menus
"""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from typing import List, Dict, Any, Optional
import math

def get_categories_keyboard(categories: List[Dict], page: int = 1, items_per_page: int = 8) -> InlineKeyboardMarkup:
    """
    Paginated categories keyboard
    """
    builder = InlineKeyboardBuilder()
    
    # Calculate pagination
    total_pages = math.ceil(len(categories) / items_per_page)
    start = (page - 1) * items_per_page
    end = start + items_per_page
    
    # Add category buttons
    for cat in categories[start:end]:
        emoji = cat.get('icon', '📌')
        builder.button(
            text=f"{emoji} {cat['name']}",
            callback_data=f"cat_{cat['id']}"
        )
    
    # Adjust to 2 columns
    builder.adjust(2)
    
    # Add pagination row
    pagination_row = []
    if page > 1:
        pagination_row.append(InlineKeyboardButton(text="◀️", callback_data=f"cat_page_{page-1}"))
    pagination_row.append(InlineKeyboardButton(text=f"{page}/{total_pages}", callback_data="current_page"))
    if page < total_pages:
        pagination_row.append(InlineKeyboardButton(text="▶️", callback_data=f"cat_page_{page+1}"))
    
    if pagination_row:
        builder.row(*pagination_row)
    
    # Add back button
    builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_main"))
    
    return builder.as_markup()

def get_masters_keyboard(masters: List[Dict], page: int = 1, items_per_page: int = 5) -> InlineKeyboardMarkup:
    """
    Paginated masters list
    """
    builder = InlineKeyboardBuilder()
    
    total_pages = math.ceil(len(masters) / items_per_page)
    start = (page - 1) * items_per_page
    end = start + items_per_page
    
    for master in masters[start:end]:
        rating_stars = '⭐' * round(master.get('rating', 0))
        text = f"{master['business_name']} {rating_stars} ({master['reviews_count']})"
        builder.button(
            text=text,
            callback_data=f"master_{master['id']}"
        )
    
    builder.adjust(1)
    
    # Pagination
    pagination_row = []
    if page > 1:
        pagination_row.append(InlineKeyboardButton(text="◀️", callback_data=f"master_page_{page-1}"))
    pagination_row.append(InlineKeyboardButton(text=f"{page}/{total_pages}", callback_data="current_page"))
    if page < total_pages:
        pagination_row.append(InlineKeyboardButton(text="▶️", callback_data=f"master_page_{page+1}"))
    
    if pagination_row:
        builder.row(*pagination_row)
    
    builder.row(
        InlineKeyboardButton(text="🔍 Сортировка", callback_data="sort_masters"),
        InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_categories")
    )
    
    return builder.as_markup()

def get_sort_keyboard() -> InlineKeyboardMarkup:
    """Sort options"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="⭐ По рейтингу", callback_data="sort_rating"),
        InlineKeyboardButton(text="💰 По цене", callback_data="sort_price")
    )
    builder.row(
        InlineKeyboardButton(text="📊 По популярности", callback_data="sort_popular"),
        InlineKeyboardButton(text="👍 По отзывам", callback_data="sort_reviews")
    )
    builder.row(
        InlineKeyboardButton(text="📍 По близости", callback_data="sort_distance"),
        InlineKeyboardButton(text="⏱ По скорости", callback_data="sort_speed")
    )
    builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_masters"))
    return builder.as_markup()

def get_service_keyboard(service: Dict) -> InlineKeyboardMarkup:
    """
    Service actions keyboard
    """
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📅 Записаться", callback_data=f"book_{service['id']}"),
        InlineKeyboardButton(text="👨‍🔧 О мастере", callback_data=f"master_info_{service['master_id']}")
    )
    builder.row(
        InlineKeyboardButton(text="⭐ Отзывы", callback_data=f"reviews_{service['id']}"),
        InlineKeyboardButton(text="📋 Похожие", callback_data=f"similar_{service['id']}")
    )
    builder.row(
        InlineKeyboardButton(text="📱 Позвонить", callback_data=f"call_{service['master_id']}"),
        InlineKeyboardButton(text="💬 Чат", callback_data=f"chat_{service['master_id']}")
    )
    builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_masters"))
    return builder.as_markup()

def get_booking_keyboard(service_id: int, available_dates: List[str]) -> InlineKeyboardMarkup:
    """
    Booking date/time selection
    """
    builder = InlineKeyboardBuilder()
    
    # Add dates
    for date in available_dates[:5]:
        builder.button(text=date, callback_data=f"date_{date}")
    
    builder.adjust(2)
    
    # Time slots will be added after date selection
    
    builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data=f"service_{service_id}"))
    
    return builder.as_markup()

def get_payment_methods_keyboard(order_id: int) -> InlineKeyboardMarkup:
    """
    Payment methods
    """
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="💳 Карта РФ", callback_data=f"pay_card_{order_id}"),
        InlineKeyboardButton(text="📱 Apple Pay", callback_data=f"pay_apple_{order_id}")
    )
    builder.row(
        InlineKeyboardButton(text="💰 Наличные", callback_data=f"pay_cash_{order_id}"),
        InlineKeyboardButton(text="💸 Перевод", callback_data=f"pay_transfer_{order_id}")
    )
    builder.row(
        InlineKeyboardButton(text="❌ Отменить заказ", callback_data=f"cancel_order_{order_id}")
    )
    return builder.as_markup()

def get_back_button(callback_data: str = "back") -> InlineKeyboardMarkup:
    """Simple back button"""
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="◀️ Назад", callback_data=callback_data))
    return builder.as_markup()

def get_pagination_keyboard(current_page: int, total_pages: int, prefix: str) -> InlineKeyboardMarkup:
    """
    Generic pagination keyboard
    """
    builder = InlineKeyboardBuilder()
    buttons = []
    
    if current_page > 1:
        buttons.append(InlineKeyboardButton(text="◀️", callback_data=f"{prefix}_page_{current_page-1}"))
    buttons.append(InlineKeyboardButton(text=f"{current_page}/{total_pages}", callback_data="noop"))
    if current_page < total_pages:
        buttons.append(InlineKeyboardButton(text="▶️", callback_data=f"{prefix}_page_{current_page+1}"))
    
    builder.row(*buttons)
    return builder.as_markup()

def get_confirmation_inline(action: str, item_id: int) -> InlineKeyboardMarkup:
    """
    Inline confirmation buttons
    """
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"confirm_{action}_{item_id}"),
        InlineKeyboardButton(text="❌ Отмена", callback_data=f"cancel_{action}_{item_id}")
    )
    return builder.as_markup()