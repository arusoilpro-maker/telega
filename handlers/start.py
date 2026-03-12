"""
Start command handler with user registration
"""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
import logging
from datetime import datetime

from services.user_service import UserService
from keyboards.reply import get_main_keyboard
from keyboards.inline import get_language_keyboard
from utils.helpers import extract_user_data
from utils.decorators import rate_limit, track_analytics
from core.database import Database

router = Router()
logger = logging.getLogger(__name__)
user_service = UserService()
db = Database()

@router.message(CommandStart())
@rate_limit(limit=5)
@track_analytics('start_command')
async def cmd_start(message: Message, state: FSMContext):
    """Handle /start command"""
    
    # Clear previous state
    await state.clear()
    
    # Extract user data
    user_data = extract_user_data(message.from_user)
    
    # Register or update user
    user = await user_service.get_or_create_user(user_data)
    
    # Send welcome message with keyboard
    await message.answer(
        f"👋 <b>Добро пожаловать в RepairMarket!</b>\n\n"
        f"Мы рады видеть вас, {user['first_name']}!\n\n"
        f"🔧 <b>Что мы предлагаем:</b>\n"
        f"• Быстрый поиск мастеров в вашем районе\n"
        f"• Прозрачные цены и отзывы\n"
        f"• Безопасная оплата онлайн\n"
        f"• Гарантия на все работы\n\n"
        f"📍 Используйте кнопки меню для навигации:",
        reply_markup=get_main_keyboard(user['role']),
        parse_mode="HTML"
    )
    
    # Send tips for new users
    if user['created_at'].date() == datetime.now().date():
        await message.answer(
            "💡 <b>Совет:</b> Заполните свой профиль, чтобы мастера могли "
            "связаться с вами быстрее!",
            parse_mode="HTML"
        )
    
    # Log event
    logger.info(f"User {message.from_user.id} started bot")

@router.message(Command("help"))
async def cmd_help(message: Message):
    """Handle /help command"""
    help_text = """
<b>🔧 Помощь по боту</b>

<b>Основные команды:</b>
/start - Главное меню
/search - Поиск мастера
/profile - Мой профиль
/orders - Мои заказы
/support - Поддержка
/faq - Частые вопросы

<b>Как найти мастера:</b>
1️⃣ Нажмите "🔧 Найти мастера"
2️⃣ Выберите категорию услуги
3️⃣ Укажите ваш район
4️⃣ Выберите мастера по рейтингу
5️⃣ Запишитесь на удобное время

<b>Оплата:</b>
💳 Банковские карты
📱 Apple Pay / Google Pay
💰 Наличные мастеру
💸 Перевод на карту

<b>Безопасность:</b>
✅ Все мастера проходят проверку
✅ Гарантия возврата средств
✅ Поддержка 24/7

По всем вопросам: @repair_support
    """
    
    await message.answer(help_text, parse_mode="HTML")

@router.message(Command("profile"))
async def cmd_profile(message: Message):
    """Handle /profile command"""
    user = await user_service.get_user_by_telegram_id(message.from_user.id)
    
    if not user:
        await message.answer("❌ Профиль не найден. Используйте /start для регистрации.")
        return
    
    profile_text = f"""
<b>👤 Мой профиль</b>

<b>Имя:</b> {user['first_name']} {user.get('last_name', '')}
<b>Телефон:</b> {user.get('phone', '❌ Не указан')}
<b>Email:</b> {user.get('email', '❌ Не указан')}
<b>Роль:</b> {"👨‍🔧 Мастер" if user['role'] == 'master' else "👤 Клиент"}
<b>Регистрация:</b> {user['created_at'].strftime('%d.%m.%Y')}
<b>Заказов:</b> {user.get('orders_count', 0)}
<b>Рейтинг:</b> ⭐ {user.get('rating', 0)} ({user.get('reviews_count', 0)})

🔧 <b>Действия:</b>
• Редактировать профиль
• Мои заказы
• Настройки уведомлений
    """
    
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="✏️ Редактировать", callback_data="edit_profile")
    keyboard.button(text="📋 Мои заказы", callback_data="my_orders")
    keyboard.button(text="⚙️ Настройки", callback_data="settings")
    keyboard.adjust(2)
    
    await message.answer(profile_text, reply_markup=keyboard.as_markup(), parse_mode="HTML")

@router.message(Command("faq"))
async def cmd_faq(message: Message):
    """Handle /faq command"""
    faq_text = """
<b>📋 Часто задаваемые вопросы</b>

<b>❓ Как найти мастера?</b>
Используйте кнопку "🔧 Найти мастера" в главном меню. Выберите категорию, укажите район и выберите подходящего мастера.

<b>❓ Как записаться?</b>
После выбора мастера нажмите "📅 Записаться", выберите удобное время и подтвердите заказ.

<b>❓ Как оплатить?</b>
Оплатить можно онлайн картой, Apple/Google Pay или наличными мастеру после выполнения работ.

<b>❓ Как оставить отзыв?</b>
После выполнения заказа вы получите уведомление с просьбой оценить работу мастера.

<b>❓ Что делать если мастер не пришел?</b>
Свяжитесь с поддержкой @repair_support, мы поможем решить проблему.

<b>❓ Как стать мастером?</b>
Нажмите "⭐ Стать мастером" в главном меню и заполните анкету.
    """
    
    await message.answer(faq_text, parse_mode="HTML")

@router.message(F.text == "⭐ Стать мастером")
async def become_master(message: Message, state: FSMContext):
    """Handle become master request"""
    
    from states import MasterRegistrationStates
    
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="✅ Начать регистрацию", callback_data="start_master_reg")
    keyboard.button(text="❌ Отмена", callback_data="cancel")
    
    await message.answer(
        "👨‍🔧 <b>Регистрация мастера</b>\n\n"
        "Чтобы стать мастером на нашей платформе, вам необходимо:\n\n"
        "1️⃣ Заполнить анкету\n"
        "2️⃣ Подтвердить квалификацию\n"
        "3️⃣ Пройти проверку\n"
        "4️⃣ Настроить профиль\n\n"
        "Это займет около 5-10 минут. Готовы начать?",
        reply_markup=keyboard.as_markup(),
        parse_mode="HTML"
    )
    
    await state.set_state(MasterRegistrationStates.basic_info)

@router.message(F.text == "📋 Мои заказы")
async def my_orders(message: Message):
    """Show user orders"""
    
    orders = await db.execute("""
        SELECT o.*, s.name as service_name, 
               u.first_name as master_name,
               mp.business_name
        FROM orders o
        JOIN services s ON o.service_id = s.id
        LEFT JOIN master_profiles mp ON o.master_id = mp.id
        LEFT JOIN users u ON mp.user_id = u.id
        WHERE o.client_id = (SELECT id FROM users WHERE telegram_id = %s)
        ORDER BY o.created_at DESC
        LIMIT 5
    """, (message.from_user.id,))
    
    if not orders:
        await message.answer("📭 У вас пока нет заказов.")
        return
    
    keyboard = InlineKeyboardBuilder()
    
    for order in orders:
        status_emoji = {
            'pending': '⏳',
            'confirmed': '✅',
            'in_progress': '🔧',
            'completed': '🎉',
            'cancelled': '❌'
        }.get(order['status'], '📦')
        
        keyboard.button(
            text=f"{status_emoji} Заказ #{order['id']} - {order['service_name']}",
            callback_data=f"order_{order['id']}"
        )
    
    keyboard.button(text="📊 Все заказы", callback_data="all_orders")
    keyboard.adjust(1)
    
    await message.answer(
        "📋 <b>Ваши последние заказы:</b>",
        reply_markup=keyboard.as_markup(),
        parse_mode="HTML"
    )

@router.message(F.text == "💬 Поддержка")
async def support(message: Message):
    """Support chat"""
    
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="📝 Написать в поддержку", url="https://t.me/repair_support")
    keyboard.button(text="❓ Частые вопросы", callback_data="faq")
    keyboard.button(text="📞 Заказать звонок", callback_data="call_request")
    keyboard.adjust(1)
    
    await message.answer(
        "💬 <b>Служба поддержки</b>\n\n"
        "Мы всегда готовы помочь вам!\n\n"
        "⏰ Время работы: 24/7\n"
        "📧 Email: support@repair.ru\n"
        "📱 Telegram: @repair_support\n\n"
        "Выберите удобный способ связи:",
        reply_markup=keyboard.as_markup(),
        parse_mode="HTML"
    )

@router.message(F.text == "⚙️ Настройки")
async def settings(message: Message):
    """User settings"""
    
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="🔔 Уведомления", callback_data="settings_notifications")
    keyboard.button(text="🌐 Язык", callback_data="settings_language")
    keyboard.button(text="📍 Город", callback_data="settings_city")
    keyboard.button(text="💰 Валюта", callback_data="settings_currency")
    keyboard.button(text="👤 Личные данные", callback_data="settings_personal")
    keyboard.button(text="🔐 Безопасность", callback_data="settings_security")
    keyboard.adjust(2)
    
    await message.answer(
        "⚙️ <b>Настройки профиля</b>\n\n"
        "Выберите раздел для настройки:",
        reply_markup=keyboard.as_markup(),
        parse_mode="HTML"
    )

@router.callback_query(F.data == "edit_profile")
async def edit_profile(callback: CallbackQuery, state: FSMContext):
    """Edit profile callback"""
    
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="📱 Телефон", callback_data="edit_phone")
    keyboard.button(text="📧 Email", callback_data="edit_email")
    keyboard.button(text="📍 Адрес", callback_data="edit_address")
    keyboard.button(text="◀️ Назад", callback_data="back_to_profile")
    keyboard.adjust(2)
    
    await callback.message.edit_text(
        "✏️ <b>Редактирование профиля</b>\n\n"
        "Выберите, что хотите изменить:",
        reply_markup=keyboard.as_markup(),
        parse_mode="HTML"
    )

@router.callback_query(F.data == "back_to_profile")
async def back_to_profile(callback: CallbackQuery):
    """Back to profile"""
    await cmd_profile(callback.message)