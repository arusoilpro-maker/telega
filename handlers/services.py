"""
Handler for browsing and selecting services.
Includes categories, service details, search, filters, AI recommendations, favorites.
"""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
import math

from services.master_service import MasterService
from services.user_service import UserService
from services.geo_service import GeoService
from ai.recommendation_engine import RecommendationEngine
from keyboards.inline import (
    get_categories_keyboard,
    get_masters_keyboard,
    get_sort_keyboard,
    get_service_keyboard
)
from keyboards.reply import get_location_keyboard
from utils.decorators import track_analytics
from config.logging_config import logger

router = Router()
master_service = MasterService()
user_service = UserService()
geo_service = GeoService()
recommender = RecommendationEngine()

@router.message(F.text == "🔧 Найти мастера")
@track_analytics('search_start')
async def find_master(message: Message, state: FSMContext):
    """Start service search"""
    await state.clear()
    
    # Get top-level categories
    categories = await master_service.get_categories(parent_id=None)
    
    if not categories:
        await message.answer("😕 Категории временно недоступны. Попробуйте позже.")
        return
    
    await message.answer(
        "🔍 <b>Поиск мастера</b>\n\nВыберите категорию услуг:",
        reply_markup=get_categories_keyboard(categories),
        parse_mode="HTML"
    )

@router.callback_query(F.data.startswith("cat_"))
async def select_category(callback: CallbackQuery, state: FSMContext):
    """Category selected – show subcategories or ask for location"""
    category_id = int(callback.data.split("_")[1])
    
    # Check if has subcategories
    subcats = await master_service.get_categories(parent_id=category_id)
    if subcats:
        # Show subcategories
        await callback.message.edit_text(
            "Выберите подкатегорию:",
            reply_markup=get_categories_keyboard(subcats, back_callback=f"back_to_cat_{category_id}")
        )
    else:
        # No subcategories – ask for location or city
        await state.update_data(category_id=category_id)
        
        # Suggest location or city selection
        builder = InlineKeyboardBuilder()
        builder.button(text="📍 Рядом со мной", callback_data="nearby_search")
        builder.button(text="🏙️ Выбрать город", callback_data="select_city")
        builder.button(text="◀️ Назад", callback_data="back_to_categories")
        builder.adjust(1)
        
        await callback.message.edit_text(
            "📍 Укажите ваше местоположение или выберите город:",
            reply_markup=builder.as_markup()
        )
    await callback.answer()

@router.callback_query(F.data == "nearby_search")
async def ask_location(callback: CallbackQuery, state: FSMContext):
    """Request user location"""
    await callback.message.answer(
        "📍 Нажмите кнопку ниже, чтобы отправить свою геопозицию:",
        reply_markup=get_location_keyboard()
    )
    await callback.answer()

@router.message(F.location)
@track_analytics('location_received')
async def handle_location(message: Message, state: FSMContext):
    """Handle location and show nearby masters"""
    lat = message.location.latitude
    lon = message.location.longitude
    
    data = await state.get_data()
    category_id = data.get('category_id')
    
    # Find masters by category and location
    masters = await master_service.find_masters_nearby(
        lat=lat, lon=lon,
        category_id=category_id,
        radius_km=10,
        limit=20
    )
    
    if not masters:
        await message.answer(
            "😕 В вашем районе пока нет мастеров по выбранной категории.\n"
            "Попробуйте расширить радиус или выбрать другую категорию.",
            reply_markup=get_categories_keyboard(await master_service.get_categories())
        )
        return
    
    # Save masters list and coordinates in state for pagination
    await state.update_data(masters=masters, lat=lat, lon=lon, page=1)
    
    await show_masters_list(message, state, page=1)

async def show_masters_list(event: Message | CallbackQuery, state: FSMContext, page: int):
    """Display paginated list of masters"""
    data = await state.get_data()
    masters = data.get('masters', [])
    lat = data.get('lat')
    lon = data.get('lon')
    
    items_per_page = 5
    total_pages = math.ceil(len(masters) / items_per_page)
    start = (page - 1) * items_per_page
    end = start + items_per_page
    page_masters = masters[start:end]
    
    # Build keyboard
    builder = InlineKeyboardBuilder()
    for m in page_masters:
        # Calculate distance if coordinates available
        dist_text = ""
        if lat and lon and m.get('latitude'):
            dist = geo_service.distance(lat, lon, m['latitude'], m['longitude'])
            dist_text = f" ({dist:.1f} км)"
        
        rating_stars = '⭐' * round(m.get('rating', 0))
        text = f"{m['business_name']} {rating_stars} ({m['reviews_count']}){dist_text}"
        builder.button(text=text, callback_data=f"master_{m['id']}")
    
    builder.adjust(1)
    
    # Pagination buttons
    pagination = []
    if page > 1:
        pagination.append(InlineKeyboardButton(text="◀️", callback_data=f"master_page_{page-1}"))
    pagination.append(InlineKeyboardButton(text=f"{page}/{total_pages}", callback_data="noop"))
    if page < total_pages:
        pagination.append(InlineKeyboardButton(text="▶️", callback_data=f"master_page_{page+1}"))
    builder.row(*pagination)
    
    # Sort and back
    builder.row(
        InlineKeyboardButton(text="🔍 Сортировка", callback_data="sort_masters"),
        InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_categories")
    )
    
    text = f"🔧 Найдено мастеров: {len(masters)}"
    if isinstance(event, Message):
        await event.answer(text, reply_markup=builder.as_markup())
    else:
        await event.message.edit_text(text, reply_markup=builder.as_markup())

@router.callback_query(F.data.startswith("master_page_"))
async def masters_page(callback: CallbackQuery, state: FSMContext):
    """Handle pagination"""
    page = int(callback.data.split("_")[2])
    await state.update_data(page=page)
    await show_masters_list(callback, state, page)
    await callback.answer()

@router.callback_query(F.data.startswith("master_"))
async def show_master_detail(callback: CallbackQuery):
    """Show master profile and services"""
    master_id = int(callback.data.split("_")[1])
    master = await master_service.get_master_profile(master_id)
    services = await master_service.get_master_services(master_id)
    
    if not master:
        await callback.answer("Мастер не найден", show_alert=True)
        return
    
    # Build master info text
    text = (
        f"👨‍🔧 <b>{master['business_name']}</b>\n"
        f"⭐ Рейтинг: {master['rating']} ({master['reviews_count']} отзывов)\n"
        f"✅ Выполнено заказов: {master['completed_orders']}\n"
        f"💰 Цены: от {master['min_price']} руб.\n"
        f"⏱ Среднее время ответа: {master['response_time']} мин\n\n"
        f"{master['short_description'] or ''}\n\n"
        f"<b>Услуги:</b>"
    )
    
    # Services list
    builder = InlineKeyboardBuilder()
    for s in services:
        builder.button(
            text=f"{s['name']} – {s['price']} руб.",
            callback_data=f"service_{s['id']}"
        )
    builder.adjust(1)
    
    # Additional buttons
    builder.row(
        InlineKeyboardButton(text="⭐ Отзывы", callback_data=f"reviews_master_{master_id}"),
        InlineKeyboardButton(text="📞 Контакты", callback_data=f"contacts_{master_id}")
    )
    builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_masters"))
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data.startswith("service_"))
async def show_service_detail(callback: CallbackQuery):
    """Show detailed service information"""
    service_id = int(callback.data.split("_")[1])
    service = await master_service.get_service(service_id)
    
    if not service:
        await callback.answer("Услуга не найдена", show_alert=True)
        return
    
    text = (
        f"🔧 <b>{service['name']}</b>\n\n"
        f"{service['description']}\n\n"
        f"💰 Цена: {service['price']} руб.\n"
        f"⏱ Длительность: {service['duration_minutes']} мин\n"
        f"👨‍🔧 Мастер: {service['master_name']}\n\n"
    )
    
    await callback.message.edit_text(
        text,
        reply_markup=get_service_keyboard(service),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data == "sort_masters")
async def sort_masters(callback: CallbackQuery, state: FSMContext):
    """Show sorting options"""
    await callback.message.edit_text(
        "🔍 Выберите тип сортировки:",
        reply_markup=get_sort_keyboard()
    )
    await callback.answer()

@router.callback_query(F.data.startswith("sort_"))
async def apply_sort(callback: CallbackQuery, state: FSMContext):
    """Apply selected sort and refresh list"""
    sort_type = callback.data.split("_")[1]
    data = await state.get_data()
    masters = data.get('masters', [])
    
    # Sort based on type
    if sort_type == "rating":
        masters.sort(key=lambda x: x.get('rating', 0), reverse=True)
    elif sort_type == "price":
        masters.sort(key=lambda x: x.get('min_price', 0))
    elif sort_type == "popular":
        masters.sort(key=lambda x: x.get('completed_orders', 0), reverse=True)
    elif sort_type == "reviews":
        masters.sort(key=lambda x: x.get('reviews_count', 0), reverse=True)
    elif sort_type == "distance" and data.get('lat') and data.get('lon'):
        # Re-calculate distance
        lat, lon = data['lat'], data['lon']
        for m in masters:
            if m.get('latitude'):
                m['distance'] = geo_service.distance(lat, lon, m['latitude'], m['longitude'])
            else:
                m['distance'] = float('inf')
        masters.sort(key=lambda x: x.get('distance', float('inf')))
    
    await state.update_data(masters=masters, page=1)
    await show_masters_list(callback, state, page=1)
    await callback.answer(f"Отсортировано по {sort_type}")

@router.callback_query(F.data == "back_to_categories")
async def back_to_categories(callback: CallbackQuery, state: FSMContext):
    """Return to category selection"""
    await state.clear()
    categories = await master_service.get_categories(parent_id=None)
    await callback.message.edit_text(
        "🔍 Выберите категорию услуг:",
        reply_markup=get_categories_keyboard(categories)
    )
    await callback.answer()

@router.callback_query(F.data == "back_to_masters")
async def back_to_masters(callback: CallbackQuery, state: FSMContext):
    """Return to masters list"""
    await show_masters_list(callback, state, page=1)
    await callback.answer()