import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from django.contrib.auth import get_user_model

User = get_user_model()

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)
from main import is_user_admin, get_premium_plan, get_bot_settings, get_user_model, create_activation_code
from info_and_utils import generate_activation_code
async def show_admin_panel(query, context):
    is_admin = await is_user_admin(query.from_user.id)
    
    if not is_admin:
        await query.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    keyboard = [
        [InlineKeyboardButton("🧪 Создать тестовый код", callback_data='admin_test_code')],
        [InlineKeyboardButton("📊 Статистика", callback_data='admin_stats')],
        [InlineKeyboardButton("« Назад", callback_data='back_to_menu')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.message.edit_text(
        "👑 <b>АДМИН ПАНЕЛЬ</b>\n\n"
        "Выберите действие:",
        parse_mode='HTML',
        reply_markup=reply_markup
    )


async def generate_test_code(query, context):
    """Генерация тестового кода для админа"""
    is_admin = await is_user_admin(query.from_user.id)
    
    if not is_admin:
        await query.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    try:
        plan = await get_premium_plan()
        code = generate_activation_code()
        
        activation_code = await create_activation_code(
            code, plan, query.from_user.id, is_test=True
        )
        
        settings = await get_bot_settings()
        
        await query.message.edit_text(
            f"🧪 <b>Тестовый код создан!</b>\n\n"
            f"Код: <code>{code}</code>\n\n"
            f"План: {plan.name}\n"
            f"Срок действия: {settings.code_expiration_hours} часов\n\n"
            f"⚠️ Это тестовый код (бесплатный)\n"
            f"Используйте в приложении AlertMe",
            parse_mode='HTML'
        )
        
        logger.info(f"🧪 Админ {query.from_user.id} создал тестовый код {code}")
        
    except Exception as e:
        logger.error(f"❌ Ошибка создания тестового кода: {e}", exc_info=True)
        await query.message.edit_text(
            "❌ Ошибка создания кода.\n\nПопробуйте позже.",
            parse_mode='HTML'
        )


async def show_admin_stats(query, context):
    """Статистика для админа"""
    is_admin = await is_user_admin(query.from_user.id)
    
    if not is_admin:
        await query.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    settings = await get_bot_settings()
    
    keyboard = [[InlineKeyboardButton("« Назад", callback_data='admin_panel')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.message.edit_text(
        f"📊 <b>Статистика бота</b>\n\n"
        f"💰 Платежей получено: <b>{settings.total_payments_received}</b>\n"
        f"🎟️ Кодов создано: <b>{settings.total_codes_generated}</b>\n"
        f"✅ Кодов активировано: <b>{settings.total_codes_activated}</b>\n\n"
        f"⚙️ <b>Настройки:</b>\n"
        f"Цена: {settings.default_price_stars} ⭐\n"
        f"Срок подписки: {settings.subscription_days} дней\n"
        f"Срок кода: {settings.code_expiration_hours} часов",
        parse_mode='HTML',
        reply_markup=reply_markup
    )
