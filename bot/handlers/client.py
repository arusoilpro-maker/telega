import io
from aiogram import Router, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove, InputFile
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from datetime import datetime, timedelta
from geopy.distance import distance  # pip install geopy

from bot.states.order_states import OrderStates
from database.crud import (
    get_services, get_masters_by_service, create_order,
    get_user_by_telegram_id, get_service_by_id, get_master_by_id,
    update_order_payment_id, get_order_by_id
)
from services.maps.google_maps import find_nearest_masters
from services.notification.notifier import notify_masters_about_new_order, notify_client
from bot.keyboards.reply import main_menu_keyboard, request_phone_keyboard, request_location_keyboard
from services.payments.payment_gateway import create_yookassa_payment, check_yookassa_payment
from services.calendar.google_calendar import add_event_to_calendar as add_google_event
from services.calendar.outlook_calendar import add_outlook_event
from config import ADMIN_IDS, GOOGLE_MAPS_API_KEY
import logging

router = Router()

# ---- Новые состояния ----
class ExtendedOrderStates(OrderStates):
    choosing_photos = State()       # загрузка фото
    choosing_payment = State()      # выбор способа оплаты
    waiting_location = State()      # запрос геолокации

# ---- Начало заказа ----
@router.message(F.text == "🔧 Заказать ремонт")
async def cmd_order(message: Message, state: FSMContext):
    services = await get_services(only_services=True)
    if not services:
        await message.answer("Услуги временно недоступны.")
        return

    # Строим клавиатуру с услугами (можно множественный выбор)
    builder = InlineKeyboardBuilder()
    for service_id, name, price in services:
        builder.button(text=f"{name} - {price} руб.", callback_data=f"service_{service_id}")
    builder.adjust(1)
    await message.answer("Выберите услугу (можно выбрать несколько, нажимая по очереди):",
                         reply_markup=builder.as_markup())
    await state.set_state(ExtendedOrderStates.choosing_service)
    await state.update_data(selected_services=[])  # список выбранных услуг

# ---- Выбор услуги (поддержка множественного выбора) ----
@router.callback_query(StateFilter(ExtendedOrderStates.choosing_service), F.data.startswith("service_"))
async def service_chosen(callback: CallbackQuery, state: FSMContext):
    service_id = int(callback.data.split("_")[1])
    data = await state.get_data()
    selected = data.get('selected_services', [])

    if service_id in selected:
        # Если уже выбрана, убираем
        selected.remove(service_id)
        await callback.answer(f"Услуга убрана")
    else:
        selected.append(service_id)
        await callback.answer(f"Услуга добавлена")

    await state.update_data(selected_services=selected)

    # Показываем текущий выбор
    services = await get_services(only_services=True)
    names = [name for sid, name, price in services if sid in selected]
    if names:
        text = f"Выбрано: {', '.join(names)}\n\nМожете выбрать ещё или нажмите 'Готово'."
    else:
        text = "Выберите услугу (можно несколько)."

    # Добавляем кнопку "Готово"
    builder = InlineKeyboardBuilder()
    for service_id, name, price in services:
        # Помечаем выбранные галочкой
        mark = "✅ " if service_id in selected else ""
        builder.button(text=f"{mark}{name} - {price} руб.", callback_data=f"service_{service_id}")
    builder.button(text="✅ Готово", callback_data="services_done")
    builder.adjust(1)

    await callback.message.edit_text(text, reply_markup=builder.as_markup())

@router.callback_query(StateFilter(ExtendedOrderStates.choosing_service), F.data == "services_done")
async def services_done(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    selected = data.get('selected_services', [])
    if not selected:
        await callback.answer("Вы не выбрали ни одной услуги!", show_alert=True)
        return

    # Сохраняем список услуг (можно сохранить как JSON)
    await state.update_data(service_ids=selected)

    # Запрашиваем локацию для поиска ближайших мастеров
    kb = ReplyKeyboardBuilder()
    kb.button(text="📍 Отправить геолокацию", request_location=True)
    kb.button(text="🔙 Отмена")
    kb.adjust(1)
    await callback.message.answer(
        "Пожалуйста, отправьте вашу геолокацию, чтобы мы нашли ближайших мастеров.\n"
        "Или нажмите 'Отмена' для ручного ввода адреса.",
        reply_markup=kb.as_markup(resize_keyboard=True)
    )
    await state.set_state(ExtendedOrderStates.waiting_location)

# ---- Обработка геолокации ----
@router.message(ExtendedOrderStates.waiting_location, F.location)
async def location_received(message: Message, state: FSMContext):
    lat = message.location.latitude
    lon = message.location.longitude
    await state.update_data(client_lat=lat, client_lon=lon)

    # Ищем ближайших мастеров (для всех выбранных услуг)
    data = await state.get_data()
    service_ids = data['service_ids']

    # Получаем всех мастеров, подходящих под любую из услуг
    all_masters = []
    for sid in service_ids:
        masters = await get_masters_by_service(sid)
        all_masters.extend(masters)

    # Убираем дубликаты мастеров (если один мастер может выполнять несколько услуг)
    unique_masters = {m[0]: m for m in all_masters}.values()

    if not unique_masters:
        await message.answer("К сожалению, сейчас нет свободных мастеров.", reply_markup=main_menu_keyboard())
        await state.clear()
        return

    # Сортируем по расстоянию
    from geopy.distance import distance
    masters_with_dist = []
    for master in unique_masters:
        master_id, name, rating, m_lat, m_lon = master  # ожидаем, что get_masters_by_service возвращает координаты
        if m_lat and m_lon:
            dist = distance((lat, lon), (m_lat, m_lon)).km
            masters_with_dist.append((master_id, name, rating, dist))
        else:
            masters_with_dist.append((master_id, name, rating, float('inf')))

    masters_with_dist.sort(key=lambda x: x[3])  # по расстоянию

    # Показываем топ-5 мастеров
    builder = InlineKeyboardBuilder()
    for master_id, name, rating, dist in masters_with_dist[:5]:
        dist_text = f"{dist:.1f} км" if dist != float('inf') else "?"
        builder.button(text=f"{name} (⭐ {rating}) - {dist_text}", callback_data=f"master_{master_id}")
    builder.adjust(1)
    await message.answer("Выберите мастера:", reply_markup=builder.as_markup())
    await state.set_state(ExtendedOrderStates.choosing_master)
    # Убираем клавиатуру с локацией
    await message.answer("Геолокация получена.", reply_markup=ReplyKeyboardRemove())

# ---- Если клиент не отправил геолокацию, запрашиваем адрес вручную ----
@router.message(ExtendedOrderStates.waiting_location, F.text == "🔙 Отмена")
async def location_cancel(message: Message, state: FSMContext):
    await message.answer("Введите ваш адрес (город, улица, дом):", reply_markup=ReplyKeyboardRemove())
    await state.set_state(ExtendedOrderStates.entering_address)

# ---- Ручной ввод адреса (без геолокации) ----
@router.message(ExtendedOrderStates.entering_address)
async def manual_address(message: Message, state: FSMContext):
    address = message.text
    await state.update_data(address=address)
    # Пропускаем поиск по расстоянию, просто показываем всех мастеров
    data = await state.get_data()
    service_ids = data['service_ids']
    all_masters = []
    for sid in service_ids:
        masters = await get_masters_by_service(sid)
        all_masters.extend(masters)
    unique_masters = {m[0]: m for m in all_masters}.values()
    if not unique_masters:
        await message.answer("Нет свободных мастеров.", reply_markup=main_menu_keyboard())
        await state.clear()
        return
    builder = InlineKeyboardBuilder()
    for master in unique_masters:
        master_id, name, rating, *_ = master
        builder.button(text=f"{name} (⭐ {rating})", callback_data=f"master_{master_id}")
    builder.adjust(1)
    await message.answer("Выберите мастера:", reply_markup=builder.as_markup())
    await state.set_state(ExtendedOrderStates.choosing_master)

# ---- Выбор мастера ----
@router.callback_query(StateFilter(ExtendedOrderStates.choosing_master), F.data.startswith("master_"))
async def master_chosen(callback: CallbackQuery, state: FSMContext):
    master_id = int(callback.data.split("_")[1])
    await state.update_data(master_id=master_id)

    # Запрашиваем желаемое время
    await callback.message.edit_text(
        "Введите желаемую дату и время в формате ДД.ММ.ГГГГ ЧЧ:ММ\n"
        "Например: 25.12.2025 14:30"
    )
    await state.set_state(ExtendedOrderStates.choosing_datetime)

# ---- Ввод даты и времени ----
@router.message(StateFilter(ExtendedOrderStates.choosing_datetime))
async def datetime_entered(message: Message, state: FSMContext):
    try:
        scheduled_time = datetime.strptime(message.text, "%d.%m.%Y %H:%M")
        if scheduled_time < datetime.now():
            await message.answer("Время не может быть в прошлом. Попробуйте снова.")
            return
        await state.update_data(scheduled_time=scheduled_time.isoformat())

        # Предлагаем загрузить фото проблемы
        kb = ReplyKeyboardBuilder()
        kb.button(text="📸 Загрузить фото")
        kb.button(text="⏩ Пропустить")
        kb.adjust(2)
        await message.answer(
            "Вы можете загрузить фотографии проблемы (до 5 фото), чтобы мастер лучше подготовился.\n"
            "Отправляйте фото по одному. Когда закончите, нажмите 'Готово'.",
            reply_markup=kb.as_markup(resize_keyboard=True)
        )
        await state.set_state(ExtendedOrderStates.choosing_photos)
        await state.update_data(photos=[])  # список file_id фото
    except ValueError:
        await message.answer("Неверный формат. Используйте ДД.ММ.ГГГГ ЧЧ:ММ")

# ---- Загрузка фото ----
@router.message(ExtendedOrderStates.choosing_photos, F.photo)
async def photo_received(message: Message, state: FSMContext):
    data = await state.get_data()
    photos = data.get('photos', [])
    # Берём самое большое фото (последнее в списке)
    file_id = message.photo[-1].file_id
    photos.append(file_id)
    await state.update_data(photos=photos)
    await message.answer(f"Фото загружено. Всего: {len(photos)}. Можете отправить ещё или нажмите 'Готово'.")

@router.message(ExtendedOrderStates.choosing_photos, F.text == "📸 Загрузить фото")
async def request_photo(message: Message, state: FSMContext):
    await message.answer("Отправьте фото.")

@router.message(ExtendedOrderStates.choosing_photos, F.text == "⏩ Пропустить")
async def skip_photos(message: Message, state: FSMContext):
    await state.update_data(photos=[])
    await show_summary(message, state)

@router.message(ExtendedOrderStates.choosing_photos, F.text == "Готово")
async def photos_done(message: Message, state: FSMContext):
    await show_summary(message, state)

async def show_summary(message: Message, state: FSMContext):
    data = await state.get_data()
    service_ids = data['service_ids']
    master_id = data['master_id']
    scheduled_time = data['scheduled_time']
    address = data.get('address', 'Геолокация определена')
    photos = data.get('photos', [])

    # Получаем названия услуг и общую стоимость
    services = []
    total_price = 0
    for sid in service_ids:
        service = await get_service_by_id(sid)
        services.append(service.name)
        total_price += service.price

    master = await get_master_by_id(master_id)

    text = (f"📋 **Подтверждение заказа**\n\n"
            f"**Услуги:** {', '.join(services)}\n"
            f"**Мастер:** {master.user.full_name}\n"
            f"**Время:** {scheduled_time}\n"
            f"**Адрес:** {address}\n"
            f"**Общая стоимость:** {total_price} руб.\n"
            f"**Фото:** {len(photos)} загружено\n\n"
            f"Выберите способ оплаты:")

    builder = InlineKeyboardBuilder()
    builder.button(text="💳 Оплатить онлайн", callback_data="pay_online")
    builder.button(text="💰 Наличными мастеру", callback_data="pay_cash")
    builder.button(text="❌ Отменить", callback_data="cancel_order")
    builder.adjust(1)

    await message.answer(text, reply_markup=builder.as_markup(), parse_mode="Markdown")
    await state.set_state(ExtendedOrderStates.choosing_payment)

# ---- Выбор оплаты ----
@router.callback_query(StateFilter(ExtendedOrderStates.choosing_payment), F.data == "pay_online")
async def pay_online(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    service_ids = data['service_ids']
    total_price = 0
    for sid in service_ids:
        service = await get_service_by_id(sid)
        total_price += service.price

    # Создаём платёж в ЮKassa
    payment_url, payment_id = await create_yookassa_payment(
        amount=total_price,
        description=f"Заказ ремонта: услуги {len(service_ids)}",
        return_url="https://t.me/SPECMASTER_ElectricHVAC_bot",  # можно передать ссылку на бота
        metadata={'telegram_id': callback.from_user.id}
    )

    # Сохраняем payment_id в состоянии
    await state.update_data(payment_id=payment_id)

    # Отправляем ссылку на оплату
    await callback.message.answer(
        f"Для оплаты перейдите по ссылке:\n{payment_url}\n\n"
        f"После оплаты нажмите кнопку ниже, чтобы подтвердить.",
        reply_markup=InlineKeyboardBuilder().button(text="✅ Я оплатил", callback_data="payment_confirmed").as_markup()
    )
    await state.set_state(ExtendedOrderStates.confirming)

@router.callback_query(StateFilter(ExtendedOrderStates.choosing_payment), F.data == "pay_cash")
async def pay_cash(callback: CallbackQuery, state: FSMContext):
    # Оплата наличными – просто создаём заказ без платежа
    await create_final_order(callback, state, payment_status="pending")

@router.callback_query(StateFilter(ExtendedOrderStates.choosing_payment), F.data == "cancel_order")
async def cancel_order(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("Заказ отменён.")
    await state.clear()
    await callback.message.answer("Главное меню:", reply_markup=main_menu_keyboard())

# ---- Подтверждение оплаты ----
@router.callback_query(StateFilter(ExtendedOrderStates.confirming), F.data == "payment_confirmed")
async def payment_confirmed(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    payment_id = data.get('payment_id')
    if payment_id:
        status = await check_yookassa_payment(payment_id)
        if status == 'succeeded':
            await create_final_order(callback, state, payment_status="paid")
        else:
            await callback.answer("Платёж ещё не прошёл или отклонён. Попробуйте позже.", show_alert=True)
    else:
        await callback.answer("Ошибка: нет payment_id", show_alert=True)

# ---- Финальное создание заказа ----
async def create_final_order(event, state, payment_status="pending"):
    """Создаёт заказ в БД, отправляет уведомления, добавляет в календарь"""
    data = await state.get_data()
    user = await get_user_by_telegram_id(event.from_user.id)

    service_ids = data['service_ids']
    master_id = data['master_id']
    scheduled_time = datetime.fromisoformat(data['scheduled_time'])
    address = data.get('address', 'Геолокация')
    photos = data.get('photos', [])
    payment_id = data.get('payment_id')

    # Рассчитываем общую стоимость
    total_price = 0
    for sid in service_ids:
        service = await get_service_by_id(sid)
        total_price += service.price

    # Создаём заказ (для простоты берём первую услугу как основную)
    # В реальности нужно хранить список услуг в отдельной таблице
    order = await create_order(
        client_id=user.id,
        master_id=master_id,
        service_id=service_ids[0],  # упрощённо
        scheduled_time=scheduled_time,
        address=address,
        total_price=total_price,
        payment_status=payment_status,
        payment_id=payment_id,
        photos=photos  # нужно добавить поле photos в модель Order или отдельную таблицу
    )

    # Уведомляем мастера
    await notify_masters_about_new_order(order)

    # Добавляем событие в Google календарь (если настроено)
    try:
        await add_google_event(
            summary=f"Ремонт: заказ #{order.id}",
            description=f"Клиент: {user.full_name}\nУслуги: {service_ids}",
            start_time=scheduled_time,
            end_time=scheduled_time + timedelta(hours=2),  # предположительная длительность
            attendees=[]
        )
    except Exception as e:
        logging.error(f"Google Calendar error: {e}")

    # Отправляем подтверждение клиенту
    await event.message.edit_text("✅ Заказ оформлен! Мастер скоро свяжется с вами.")
    if payment_status == "paid":
        await event.message.answer("💳 Оплата получена. Спасибо!")
    else:
        await event.message.answer("💰 Оплата наличными мастеру при выполнении.")

    await state.clear()
    await event.message.answer("Главное меню:", reply_markup=main_menu_keyboard())
    
# В client.py в datetime_entered после успешного парсинга:
master_id = data['master_id']
# Получаем длительность (можно из модели услуги или фиксированную)
duration_hours = 2
start_time = scheduled_time
end_time = start_time + timedelta(hours=duration_hours)

if not await is_master_available(master_id, start_time, end_time):
    await message.answer("Мастер занят в это время. Выберите другое время.")
    return

# В create_final_order после создания заказа:
await add_master_busy_slot(master_id, scheduled_time, scheduled_time + timedelta(hours=2), order.id)

@router.callback_query(F.data.startswith("rate_"))
async def process_rating(callback: CallbackQuery):
    parts = callback.data.split("_")
    order_id = int(parts[1])
    rating = int(parts[2])
    # Сохраняем оценку в заказе
    await update_order_review(order_id, rating)
    await callback.message.edit_text(f"Спасибо за оценку! Вы поставили {rating} звёзд.")
    # Можно также попросить текстовый отзыв
    # Для этого можно использовать FSM или просто следующее сообщение
    await callback.message.answer("Если хотите, можете оставить текстовый отзыв:")

@router.message(F.text & ~F.text.startswith("/") & F.reply_to_message)  # пример фильтра
async def text_review(message: Message):
    # Упрощённо: ищем последний заказ клиента и добавляем отзыв
    # Лучше использовать FSM
    pass

@router.message(Command("my_orders"))
@router.message(F.text == "📋 Мои заказы")
async def my_orders(message: Message):
    orders = await get_client_orders(message.from_user.id)
    if not orders:
        await message.answer("У вас пока нет заказов.")
        return

    text = "Ваши заказы:\n\n"
    for order in orders:
        # Получаем названия услуг
        services_names = [s.name for s in order.services]
        status_emoji = {
            "new": "🆕", "assigned": "👨‍🔧", "done": "✅", "cancelled": "❌"
        }.get(order.status, "⏳")
        text += f"{status_emoji} Заказ #{order.id} от {order.created_at.strftime('%d.%m.%Y %H:%M')}\n"
        text += f"Услуги: {', '.join(services_names)}\n"
        text += f"Мастер: {order.master.user.full_name if order.master else 'не назначен'}\n"
        text += f"Статус: {order.status}\n"
        text += f"Сумма: {order.total_price} руб.\n"
        if order.review_rating:
            text += f"Ваша оценка: {order.review_rating} ⭐\n"
        text += "\n"
    await message.answer(text[:4000])  # ограничение длины
    
@router.message(Command("my_orders"))
@router.message(F.text == "📋 Мои заказы")
async def my_orders(message: Message):
    orders = await get_client_orders(message.from_user.id)
    if not orders:
        await message.answer("У вас пока нет заказов.")
        return

    for order in orders:
        services_names = [s.name for s in order.services]
        status_emoji = {"new": "🆕", "assigned": "👨‍🔧", "done": "✅", "cancelled": "❌"}.get(order.status, "⏳")
        text = f"{status_emoji} Заказ #{order.id} от {order.created_at.strftime('%d.%m.%Y %H:%M')}\n"
        text += f"Услуги: {', '.join(services_names)}\n"
        text += f"Мастер: {order.master.user.full_name if order.master else 'не назначен'}\n"
        text += f"Статус: {order.status}\n"
        text += f"Сумма: {order.total_price} руб.\n"

        builder = InlineKeyboardBuilder()
        if order.status in ["new", "assigned"]:
            builder.button(text="❌ Отменить заказ", callback_data=f"cancel_order_{order.id}")
        # Можно добавить кнопку "Повторить" для выполненных
        if order.status == "done":
            builder.button(text="🔁 Заказать снова", callback_data=f"repeat_order_{order.id}")
        await message.answer(text, reply_markup=builder.as_markup())

@router.callback_query(F.data.startswith("cancel_order_"))
async def cancel_order_callback(callback: CallbackQuery):
    order_id = int(callback.data.split("_")[2])
    # Обновляем статус
    await update_order_status(order_id, "cancelled")
    # Освобождаем слот в расписании мастера (удаляем занятость)
    await remove_master_busy_slot_by_order(order_id)
    await callback.message.edit_text("Заказ отменён.")

# В crud.py добавить функцию удаления слота
async def remove_master_busy_slot_by_order(order_id):
    async with get_session() as session:
        await session.execute(
            delete(MasterSchedule).where(MasterSchedule.order_id == order_id)
        )
        await session.commit()
        
class Master(Base):
    # ... существующие поля ...
    average_rating = Column(Float, default=0.0)
    reviews_count = Column(Integer, default=0)

async def update_master_rating(master_id):
    async with get_session() as session:
        # Вычисляем средний рейтинг из всех заказов этого мастера, где есть review_rating
        result = await session.execute(
            select(func.avg(Order.review_rating), func.count(Order.id))
            .where(Order.master_id == master_id, Order.review_rating.isnot(None))
        )
        avg, count = result.first()
        if avg:
            await session.execute(
                update(Master)
                .where(Master.id == master_id)
                .values(average_rating=avg, reviews_count=count)
            )
            await session.commit()