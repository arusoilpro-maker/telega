from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from database.crud import get_master_orders
from services.notification.notifier import notify_master

router = Router()

@router.message(Command("my_orders"))
async def my_orders(message: Message):
    # Показываем мастеру его заказы
    orders = await get_master_orders(message.from_user.id)
    if not orders:
        await message.answer("У вас пока нет заказов.")
        return
    text = "Ваши заказы:\n"
    for order in orders:
        text += f"🔧 {order.service.name} - {order.scheduled_time} - {order.status}\n"
    await message.answer(text)

# Мастер может подтвердить выполнение заказа
@router.callback_query(F.data.startswith("complete_order_"))
async def complete_order(callback: CallbackQuery):
    order_id = int(callback.data.split("_")[2])
    # Обновляем статус заказа в БД
    await update_order_status(order_id, "done")
    await callback.message.edit_text("Заказ выполнен. Спасибо!")
    # Отправляем уведомление клиенту (через бота)
    client_tg_id = await get_client_telegram_id_by_order(order_id)
    await callback.bot.send_message(client_tg_id, "Ваш заказ выполнен! Оставьте отзыв о мастере.")
    
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from database.crud import update_order_status, get_order_by_id, get_client_telegram_id

@router.callback_query(F.data.startswith("complete_order_"))
async def complete_order(callback: CallbackQuery):
    order_id = int(callback.data.split("_")[2])
    await update_order_status(order_id, "done", completed_at=datetime.now())
    await callback.message.edit_text("Заказ выполнен. Спасибо!")

    # Отправляем уведомление клиенту с предложением оставить отзыв
    order = await get_order_by_id(order_id)
    if order and order.client:
        client_tg_id = order.client.telegram_id
        if client_tg_id:
            # Кнопки для оценки
            builder = InlineKeyboardBuilder()
            for i in range(1, 6):
                builder.button(text=f"{i} ⭐", callback_data=f"rate_{order_id}_{i}")
            builder.adjust(5)
            await callback.bot.send_message(
                client_tg_id,
                f"Мастер {order.master.user.full_name} выполнил ваш заказ. Пожалуйста, оцените качество работы (1-5 звёзд):",
                reply_markup=builder.as_markup()
            )