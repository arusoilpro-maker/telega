"""
Handler for booking process: date/time selection, confirmation, payment.
"""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, LabeledPrice, PreCheckoutQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from datetime import datetime, timedelta
import logging

from services.order_service import OrderService
from services.master_service import MasterService
from services.payment_service import PaymentService
from services.notification_service import NotificationService
from keyboards.inline import get_booking_keyboard, get_payment_methods_keyboard, get_confirmation_inline
from keyboards.reply import get_confirmation_keyboard
from utils.decorators import track_analytics
from config.settings import config

router = Router()
order_service = OrderService()
master_service = MasterService()
payment_service = PaymentService()
notifier = NotificationService()
logger = logging.getLogger(__name__)

class BookingStates(StatesGroup):
    selecting_date = State()
    selecting_time = State()
    confirming = State()
    payment_method = State()
    processing_payment = State()

@router.callback_query(F.data.startswith("book_"))
async def start_booking(callback: CallbackQuery, state: FSMContext):
    """Start booking process for a service"""
    service_id = int(callback.data.split("_")[1])
    service = await master_service.get_service(service_id)
    
    if not service:
        await callback.answer("Услуга не найдена", show_alert=True)
        return
    
    # Check if master is available (simple check)
    master = await master_service.get_master_profile(service['master_id'])
    if not master or not master['is_online']:
        await callback.answer("Мастер временно недоступен", show_alert=True)
        return
    
    await state.update_data(
        service_id=service_id,
        master_id=service['master_id'],
        service_name=service['name'],
        price=service['price']
    )
    
    # Show available dates (next 7 days)
    dates = [(datetime.now() + timedelta(days=i)).strftime("%d.%m.%Y") for i in range(1, 8)]
    await callback.message.edit_text(
        f"📅 Выберите дату для услуги <b>{service['name']}</b>:",
        reply_markup=get_booking_keyboard(service_id, dates),
        parse_mode="HTML"
    )
    await state.set_state(BookingStates.selecting_date)
    await callback.answer()

@router.callback_query(F.data.startswith("date_"), BookingStates.selecting_date)
async def select_date(callback: CallbackQuery, state: FSMContext):
    """Date selected – show available time slots"""
    date_str = callback.data.split("_")[1]
    await state.update_data(selected_date=date_str)
    
    # Get master's working hours and generate available slots
    data = await state.get_data()
    master_id = data['master_id']
    
    # Mock available times (9:00-18:00 every 2 hours)
    available_times = ["09:00", "11:00", "13:00", "15:00", "17:00"]
    
    builder = InlineKeyboardBuilder()
    for t in available_times:
        builder.button(text=t, callback_data=f"time_{t}")
    builder.adjust(3)
    builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_dates"))
    
    await callback.message.edit_text(
        f"🕐 Выберите удобное время на {date_str}:",
        reply_markup=builder.as_markup()
    )
    await state.set_state(BookingStates.selecting_time)
    await callback.answer()

@router.callback_query(F.data.startswith("time_"), BookingStates.selecting_time)
async def select_time(callback: CallbackQuery, state: FSMContext):
    """Time selected – show confirmation"""
    time_str = callback.data.split("_")[1]
    await state.update_data(selected_time=time_str)
    
    data = await state.get_data()
    service_name = data['service_name']
    price = data['price']
    date = data['selected_date']
    time = time_str
    
    # Calculate total with platform commission
    commission = config.PLATFORM_COMMISSION
    total = price * (1 + commission / 100)
    
    await state.update_data(total=total)
    
    summary = (
        f"📋 <b>Подтверждение заказа</b>\n\n"
        f"🔧 Услуга: {service_name}\n"
        f"📅 Дата: {date}\n"
        f"🕐 Время: {time}\n"
        f"💰 Стоимость услуги: {price} руб.\n"
        f"📊 Комиссия платформы ({commission}%): {price * commission / 100:.2f} руб.\n"
        f"💵 <b>Итого к оплате: {total:.2f} руб.</b>\n\n"
        f"Всё верно?"
    )
    
    await callback.message.edit_text(
        summary,
        reply_markup=get_confirmation_inline("booking", data['service_id']),
        parse_mode="HTML"
    )
    await state.set_state(BookingStates.confirming)
    await callback.answer()

@router.callback_query(F.data.startswith("confirm_booking_"), BookingStates.confirming)
async def confirm_booking(callback: CallbackQuery, state: FSMContext):
    """User confirmed booking – proceed to payment method selection"""
    data = await state.get_data()
    
    # Create order in database (pending)
    user = await user_service.get_user_by_telegram_id(callback.from_user.id)
    order_id = await order_service.create_order(
        client_id=user['id'],
        master_id=data['master_id'],
        service_id=data['service_id'],
        scheduled_date=data['selected_date'],
        scheduled_time=data['selected_time'],
        total_amount=data['total']
    )
    
    await state.update_data(order_id=order_id)
    
    await callback.message.edit_text(
        "💳 Выберите способ оплаты:",
        reply_markup=get_payment_methods_keyboard(order_id)
    )
    await state.set_state(BookingStates.payment_method)
    await callback.answer()

@router.callback_query(F.data.startswith("pay_"), BookingStates.payment_method)
async def select_payment_method(callback: CallbackQuery, state: FSMContext):
    """Handle payment method selection"""
    method = callback.data.split("_")[1]
    order_id = int(callback.data.split("_")[2])
    
    data = await state.get_data()
    total = data['total']
    
    if method == "card":
        # Stripe integration
        await callback.message.edit_text(
            "🔐 Перенаправляем на страницу оплаты...",
            reply_markup=None
        )
        # Create payment intent
        payment_intent = await payment_service.create_stripe_payment(
            amount=int(total * 100),  # in cents
            order_id=order_id,
            user_id=callback.from_user.id
        )
        # Send payment link (simplified)
        builder = InlineKeyboardBuilder()
        builder.button(text="💳 Оплатить", url=payment_intent['url'])
        builder.button(text="✅ Проверить оплату", callback_data=f"check_payment_{order_id}")
        await callback.message.answer(
            "Для оплаты нажмите кнопку ниже:",
            reply_markup=builder.as_markup()
        )
    elif method == "cash":
        # Cash payment – order confirmed without online payment
        await order_service.confirm_order(order_id, payment_method='cash')
        await callback.message.edit_text(
            "✅ Заказ подтверждён! Мастер свяжется с вами для уточнения деталей.\n"
            "Оплата наличными после выполнения работ."
        )
        # Notify master
        await notifier.notify_master_new_order(order_id)
        await state.clear()
    else:
        await callback.answer("Данный способ оплаты временно недоступен", show_alert=True)

@router.callback_query(F.data.startswith("check_payment_"))
async def check_payment(callback: CallbackQuery, state: FSMContext):
    """Check if payment was completed"""
    order_id = int(callback.data.split("_")[2])
    order = await order_service.get_order(order_id)
    
    if order['payment_status'] == 'paid':
        await callback.message.edit_text(
            "✅ Оплата получена! Заказ подтверждён."
        )
        await notifier.notify_master_new_order(order_id)
        await state.clear()
    else:
        await callback.answer("Оплата ещё не поступила. Попробуйте позже.", show_alert=True)

@router.pre_checkout_query()
async def pre_checkout_handler(pre_checkout_q: PreCheckoutQuery):
    """Handle pre-checkout for Telegram Stars (if used)"""
    await pre_checkout_q.answer(ok=True)

@router.message(F.successful_payment)
async def successful_payment(message: Message, state: FSMContext):
    """Handle successful payment via Telegram Stars"""
    await message.answer(
        f"✅ Оплата {message.successful_payment.total_amount // 100} "
        f"{message.successful_payment.currency} прошла успешно! Заказ подтверждён."
    )
    # Update order status
    # ... 
    await state.clear()

@router.callback_query(F.data.startswith("cancel_order_"))
async def cancel_order_flow(callback: CallbackQuery, state: FSMContext):
    """Cancel order during booking"""
    await state.clear()
    await callback.message.edit_text("❌ Заказ отменён.")
    await callback.answer()