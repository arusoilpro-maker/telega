"""
Handler for reviews: viewing, adding, managing.
"""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from datetime import datetime

from services.review_service import ReviewService
from services.order_service import OrderService
from keyboards.inline import get_back_button
from keyboards.reply import get_rating_keyboard, get_cancel_keyboard
from utils.decorators import track_analytics

router = Router()
review_service = ReviewService()
order_service = OrderService()

class ReviewStates(StatesGroup):
    selecting_order = State()
    rating = State()
    text_review = State()
    confirm = State()

@router.callback_query(F.data.startswith("reviews_master_"))
async def show_master_reviews(callback: CallbackQuery):
    """Show all reviews for a master"""
    master_id = int(callback.data.split("_")[2])
    
    # Get master info
    from services.master_service import MasterService
    master_service = MasterService()
    master = await master_service.get_master_profile(master_id)
    
    # Get reviews
    reviews = await review_service.get_master_reviews(master_id, limit=10)
    
    if not reviews:
        await callback.message.edit_text(
            f"У мастера {master['business_name']} пока нет отзывов.\n\n"
            "Вы можете оставить отзыв после заказа.",
            reply_markup=get_back_button(f"master_{master_id}")
        )
        await callback.answer()
        return
    
    text = f"⭐ <b>Отзывы о {master['business_name']}</b>\n"
    text += f"Средний рейтинг: {master['rating']} ({master['reviews_count']} отзывов)\n\n"
    
    builder = InlineKeyboardBuilder()
    for rev in reviews[:5]:
        stars = '⭐' * rev['rating']
        date_str = rev['created_at'].strftime('%d.%m.%Y')
        builder.button(
            text=f"{stars} {date_str} – {rev['reviewer_name']}",
            callback_data=f"review_{rev['id']}"
        )
    builder.adjust(1)
    
    if len(reviews) > 5:
        builder.button(text="📖 Все отзывы", callback_data=f"all_reviews_{master_id}")
    
    builder.button(text="◀️ Назад", callback_data=f"master_{master_id}")
    builder.adjust(1)
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data.startswith("review_"))
async def show_single_review(callback: CallbackQuery):
    """Show detailed review"""
    review_id = int(callback.data.split("_")[1])
    review = await review_service.get_review(review_id)
    
    if not review:
        await callback.answer("Отзыв не найден", show_alert=True)
        return
    
    stars = '⭐' * review['rating']
    text = (
        f"⭐ <b>Отзыв от {review['reviewer_name']}</b>\n"
        f"Рейтинг: {stars}\n"
        f"Дата: {review['created_at'].strftime('%d.%m.%Y')}\n\n"
        f"<i>{review['text']}</i>\n\n"
    )
    if review.get('master_response'):
        text += f"👨‍🔧 <b>Ответ мастера:</b>\n{review['master_response']}\n"
    
    builder = InlineKeyboardBuilder()
    builder.button(text="◀️ Назад", callback_data=f"reviews_master_{review['master_id']}")
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data == "leave_review")
async def start_review(callback: CallbackQuery, state: FSMContext):
    """Start leaving a review (for completed orders)"""
    # Find completed orders for this user
    user = await user_service.get_user_by_telegram_id(callback.from_user.id)
    completed_orders = await order_service.get_completed_orders_without_review(user['id'])
    
    if not completed_orders:
        await callback.answer("Нет завершённых заказов для отзыва", show_alert=True)
        return
    
    builder = InlineKeyboardBuilder()
    for order in completed_orders:
        builder.button(
            text=f"{order['service_name']} от {order['completed_date']}",
            callback_data=f"review_order_{order['id']}"
        )
    builder.adjust(1)
    builder.button(text="◀️ Назад", callback_data="back_to_profile")
    
    await callback.message.edit_text(
        "Выберите заказ, по которому хотите оставить отзыв:",
        reply_markup=builder.as_markup()
    )
    await state.set_state(ReviewStates.selecting_order)
    await callback.answer()

@router.callback_query(F.data.startswith("review_order_"), ReviewStates.selecting_order)
async def review_order_selected(callback: CallbackQuery, state: FSMContext):
    """Order selected – ask for rating"""
    order_id = int(callback.data.split("_")[2])
    await state.update_data(order_id=order_id)
    
    await callback.message.answer(
        "Оцените качество работы (1 – плохо, 5 – отлично):",
        reply_markup=get_rating_keyboard()
    )
    await state.set_state(ReviewStates.rating)
    await callback.answer()

@router.message(ReviewStates.rating, F.text)
async def process_rating(message: Message, state: FSMContext):
    """Process rating input"""
    text = message.text.strip()
    if text.startswith("⭐"):
        try:
            rating = int(text.split()[1])
            if 1 <= rating <= 5:
                await state.update_data(rating=rating)
                await message.answer(
                    "Напишите ваш отзыв (можно оставить пустым, если не хотите писать):",
                    reply_markup=get_cancel_keyboard()
                )
                await state.set_state(ReviewStates.text_review)
                return
        except:
            pass
    
    await message.answer("Пожалуйста, выберите оценку от 1 до 5, используя кнопки.")

@router.message(ReviewStates.text_review)
async def process_review_text(message: Message, state: FSMContext):
    """Process review text"""
    review_text = message.text if message.text != "❌ Отмена" else ""
    await state.update_data(text=review_text)
    
    data = await state.get_data()
    rating = data['rating']
    text = data['text']
    
    confirm_text = f"Ваш отзыв:\n⭐ {rating}\n📝 {text if text else '(без текста)'}\n\nОтправить?"
    await message.answer(
        confirm_text,
        reply_markup=get_confirmation_inline("submit_review", data['order_id'])
    )
    await state.set_state(ReviewStates.confirm)

@router.callback_query(F.data.startswith("confirm_submit_review_"), ReviewStates.confirm)
async def submit_review(callback: CallbackQuery, state: FSMContext):
    """Save review to database"""
    order_id = int(callback.data.split("_")[3])
    data = await state.get_data()
    
    # Save review
    review_id = await review_service.create_review(
        order_id=order_id,
        rating=data['rating'],
        text=data.get('text', '')
    )
    
    await callback.message.edit_text(
        "✅ Спасибо за ваш отзыв! Он поможет другим пользователям."
    )
    await state.clear()
    await callback.answer()

@router.message(F.text == "⭐ Оставить отзыв")
async def leave_review_menu(message: Message, state: FSMContext):
    """Entry point from main menu"""
    await start_review(message, state)  # reuse callback logic