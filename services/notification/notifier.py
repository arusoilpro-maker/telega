import logging
from aiogram import Bot
from config import BOT_TOKEN
from database.crud import get_master_telegram_id_by_order, get_master_by_id

bot = Bot(token=BOT_TOKEN)

async def notify_masters_about_new_order(order):
    """Отправляет уведомление мастеру о новом заказе"""
    master_tg_id = await get_master_telegram_id_by_order(order.master_id)
    if not master_tg_id:
        logging.warning(f"Мастер с ID {order.master_id} не имеет Telegram ID")
        return

    text = (f"🔔 Новый заказ!\n"
            f"Услуга: {order.service.name}\n"
            f"Клиент: {order.client.full_name}\n"
            f"Время: {order.scheduled_time}\n"
            f"Адрес: {order.address}\n"
            f"Цена: {order.total_price} руб.\n\n"
            f"Пожалуйста, подтвердите готовность.")
    try:
        await bot.send_message(chat_id=master_tg_id, text=text)
    except Exception as e:
        logging.error(f"Ошибка отправки уведомления мастеру: {e}")

async def notify_master(master_id, message):
    """Отправляет произвольное сообщение мастеру"""
    master_tg_id = await get_master_telegram_id_by_order(master_id)
    if master_tg_id:
        await bot.send_message(chat_id=master_tg_id, text=message)
        
async def notify_client(telegram_id, message):
    try:
        await bot.send_message(chat_id=telegram_id, text=message)
    except Exception as e:
        logging.error(f"Ошибка отправки клиенту {telegram_id}: {e}")