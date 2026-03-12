"""
Keyboard builders for dynamic creation
"""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from typing import List, Dict, Any, Optional, Union, Tuple

class KeyboardBuilder:
    """Helper class for building keyboards"""
    
    @staticmethod
    def inline_from_list(
        buttons: List[Tuple[str, str]],
        row_width: int = 2,
        back_button: Optional[Tuple[str, str]] = None
    ) -> InlineKeyboardMarkup:
        """
        Create inline keyboard from list of (text, callback_data) tuples
        
        Args:
            buttons: List of (text, callback_data)
            row_width: Number of buttons per row
            back_button: Optional (text, callback_data) for back button
        
        Returns:
            InlineKeyboardMarkup
        """
        builder = InlineKeyboardBuilder()
        
        for text, cb in buttons:
            builder.button(text=text, callback_data=cb)
        
        builder.adjust(row_width)
        
        if back_button:
            builder.row(InlineKeyboardButton(text=back_button[0], callback_data=back_button[1]))
        
        return builder.as_markup()
    
    @staticmethod
    def reply_from_list(buttons: List[str], row_width: int = 2, one_time: bool = False) -> ReplyKeyboardMarkup:
        """
        Create reply keyboard from list of button texts
        
        Args:
            buttons: List of button texts
            row_width: Number of buttons per row
            one_time: One-time keyboard flag
        
        Returns:
            ReplyKeyboardMarkup
        """
        builder = ReplyKeyboardBuilder()
        
        for text in buttons:
            builder.add(KeyboardButton(text=text))
        
        builder.adjust(row_width)
        
        return builder.as_markup(resize_keyboard=True, one_time_keyboard=one_time)
    
    @staticmethod
    def paginated_inline(
        items: List[Dict],
        text_field: str,
        callback_prefix: str,
        page: int = 1,
        per_page: int = 10,
        back_callback: str = None
    ) -> InlineKeyboardMarkup:
        """
        Create paginated inline keyboard from list of items
        
        Args:
            items: List of dicts with item data
            text_field: Field name to use as button text
            callback_prefix: Prefix for callback data (will be appended with item id)
            page: Current page
            per_page: Items per page
            back_callback: Callback for back button
        
        Returns:
            InlineKeyboardMarkup
        """
        builder = InlineKeyboardBuilder()
        
        total_pages = (len(items) + per_page - 1) // per_page
        start = (page - 1) * per_page
        end = start + per_page
        
        for item in items[start:end]:
            text = item.get(text_field, str(item.get('id', '')))
            callback = f"{callback_prefix}_{item['id']}"
            builder.button(text=text, callback_data=callback)
        
        builder.adjust(1)
        
        # Pagination row
        pagination = []
        if page > 1:
            pagination.append(InlineKeyboardButton(text="◀️", callback_data=f"page_{callback_prefix}_{page-1}"))
        pagination.append(InlineKeyboardButton(text=f"{page}/{total_pages}", callback_data="noop"))
        if page < total_pages:
            pagination.append(InlineKeyboardButton(text="▶️", callback_data=f"page_{callback_prefix}_{page+1}"))
        
        builder.row(*pagination)
        
        if back_callback:
            builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data=back_callback))
        
        return builder.as_markup()
    
    @staticmethod
    def with_actions(
        main_buttons: List[Tuple[str, str]],
        action_buttons: List[Tuple[str, str]],
        row_width: int = 2
    ) -> InlineKeyboardMarkup:
        """
        Combine main and action buttons
        
        Args:
            main_buttons: List of (text, callback) for main buttons
            action_buttons: List of (text, callback) for action buttons (e.g., back, sort)
            row_width: Number of main buttons per row
        
        Returns:
            InlineKeyboardMarkup
        """
        builder = InlineKeyboardBuilder()
        
        for text, cb in main_buttons:
            builder.button(text=text, callback_data=cb)
        
        builder.adjust(row_width)
        
        # Add action buttons as separate rows
        for text, cb in action_buttons:
            builder.row(InlineKeyboardButton(text=text, callback_data=cb))
        
        return builder.as_markup()


# Convenience functions
def create_inline_keyboard(
    buttons: List[Dict[str, str]],
    row_width: int = 2,
    back: Optional[Dict[str, str]] = None
) -> InlineKeyboardMarkup:
    """
    Create inline keyboard from list of button dicts
    
    Args:
        buttons: List of dicts with 'text' and 'callback_data' or 'url'
        row_width: Buttons per row
        back: Optional back button dict
    
    Returns:
        InlineKeyboardMarkup
    """
    builder = InlineKeyboardBuilder()
    
    for btn in buttons:
        if 'url' in btn:
            builder.button(text=btn['text'], url=btn['url'])
        else:
            builder.button(text=btn['text'], callback_data=btn.get('callback_data', 'noop'))
    
    builder.adjust(row_width)
    
    if back:
        if 'url' in back:
            builder.row(InlineKeyboardButton(text=back['text'], url=back['url']))
        else:
            builder.row(InlineKeyboardButton(text=back['text'], callback_data=back.get('callback_data', 'back')))
    
    return builder.as_markup()

def create_reply_keyboard(buttons: List[str], row_width: int = 2, one_time: bool = False) -> ReplyKeyboardMarkup:
    """Create reply keyboard from list of strings"""
    builder = ReplyKeyboardBuilder()
    for text in buttons:
        builder.add(KeyboardButton(text=text))
    builder.adjust(row_width)
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=one_time)

def create_pagination_buttons(
    current: int,
    total: int,
    prefix: str,
    back: Optional[str] = None
) -> List[InlineKeyboardButton]:
    """Create pagination buttons list"""
    buttons = []
    if current > 1:
        buttons.append(InlineKeyboardButton(text="◀️", callback_data=f"{prefix}_page_{current-1}"))
    buttons.append(InlineKeyboardButton(text=f"{current}/{total}", callback_data="noop"))
    if current < total:
        buttons.append(InlineKeyboardButton(text="▶️", callback_data=f"{prefix}_page_{current+1}"))
    return buttons