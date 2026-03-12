from aiogram import Router, types
from aiogram.filters import CommandStart
from bot.keyboards.reply import main_menu_keyboard

router = Router()

@router.message(CommandStart())
async def cmd_start(message: types.Message):
    await message.answer(
        "Добро пожаловать в Сервис Ремонт КАЧЕСТВЕННО ВЫГОДНО!\n"
        "Выберите действие:",
        reply_markup=main_menu_keyboard()
    )