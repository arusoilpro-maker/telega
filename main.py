import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from config import BOT_TOKEN
from database.db import init_db
from bot.handlers import client, master, admin, common
from bot.middlewares.auth import AuthMiddleware
from services.ai.ml_model import retrain_model_periodically
import asyncio

logging.basicConfig(level=logging.INFO)

async def main():
    await init_db()
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())
    bot = Bot(token=os.getenv("BOT_TOKEN"))

    dp.message.middleware(AuthMiddleware())
    dp.callback_query.middleware(AuthMiddleware())

    dp.include_router(common.router)
    dp.include_router(client.router)
    dp.include_router(master.router)
    dp.include_router(admin.router)

    # Запускаем фоновую задачу для переобучения модели
    asyncio.create_task(retrain_model_periodically())

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
    
async def main():
    await init_db()
    bot = Bot(token=BOT_TOKEN)  # Токен подставляется из config.py
    # ... остальной код