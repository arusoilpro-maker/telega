import io
import csv
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, Document, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from database.crud import add_service, add_master, get_user_by_telegram_id
from config import ADMIN_IDS

router = Router()

class UploadStates(StatesGroup):
    waiting_for_services_file = State()
    waiting_for_masters_file = State()

# Проверка на админа
def is_admin(user_id):
    return user_id in ADMIN_IDS

# Команда для загрузки услуг через CSV
@router.message(Command("upload_services"))
async def cmd_upload_services(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.answer("У вас нет прав администратора.")
        return
    await message.answer("Отправьте CSV-файл с услугами. Формат: название, описание, цена, категория (опционально), is_product (0/1), stock_quantity")
    await state.set_state(UploadStates.waiting_for_services_file)

@router.message(UploadStates.waiting_for_services_file, F.document)
async def process_services_file(message: Message, state: FSMContext):
    document = message.document
    if not document.file_name.endswith('.csv'):
        await message.answer("Пожалуйста, отправьте файл в формате CSV.")
        return

    file = await message.bot.download(document)
    csv_data = file.read().decode('utf-8')
    reader = csv.reader(io.StringIO(csv_data))
    next(reader)  # пропускаем заголовок, если есть

    added = 0
    errors = []
    for row in reader:
        if len(row) < 3:
            continue
        name = row[0].strip()
        description = row[1].strip() if len(row) > 1 else ""
        price = float(row[2]) if row[2] else 0.0
        category = row[3].strip() if len(row) > 3 else ""
        is_product = bool(int(row[4])) if len(row) > 4 else False
        stock = int(row[5]) if len(row) > 5 else 0
        try:
            await add_service(
                name=name,
                description=description,
                price=price,
                category=category,
                is_product=is_product,
                stock_quantity=stock
            )
            added += 1
        except Exception as e:
            errors.append(f"{name}: {str(e)}")
    await message.answer(f"Загружено услуг: {added}\nОшибки: {len(errors)}\n" + "\n".join(errors[:5]))
    await state.clear()

# Команда для загрузки мастеров через CSV
@router.message(Command("upload_masters"))
async def cmd_upload_masters(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.answer("У вас нет прав администратора.")
        return
    await message.answer("Отправьте CSV-файл с мастерами. Формат: telegram_id, specialty, rating, lat, lon, experience, is_available")
    await state.set_state(UploadStates.waiting_for_masters_file)

@router.message(UploadStates.waiting_for_masters_file, F.document)
async def process_masters_file(message: Message, state: FSMContext):
    document = message.document
    if not document.file_name.endswith('.csv'):
        await message.answer("Пожалуйста, отправьте файл в формате CSV.")
        return

    file = await message.bot.download(document)
    csv_data = file.read().decode('utf-8')
    reader = csv.reader(io.StringIO(csv_data))
    next(reader)

    added = 0
    errors = []
    for row in reader:
        if len(row) < 5:
            continue
        telegram_id = int(row[0])
        specialty = row[1]
        rating = float(row[2]) if row[2] else 0.0
        lat = float(row[3]) if row[3] else None
        lon = float(row[4]) if row[4] else None
        experience = int(row[5]) if len(row) > 5 else 0
        is_available = bool(int(row[6])) if len(row) > 6 else True

        # Находим или создаём пользователя
        user = await get_user_by_telegram_id(telegram_id)
        if not user:
            errors.append(f"Пользователь с telegram_id {telegram_id} не найден в базе пользователей. Сначала он должен запустить бота.")
            continue

        try:
            await add_master(
                user_id=user.id,
                specialty=specialty,
                rating=rating,
                location_lat=lat,
                location_lon=lon,
                experience_years=experience,
                is_available=is_available
            )
            added += 1
        except Exception as e:
            errors.append(f"{telegram_id}: {str(e)}")
    await message.answer(f"Загружено мастеров: {added}\nОшибки: {len(errors)}\n" + "\n".join(errors[:5]))
    await state.clear()