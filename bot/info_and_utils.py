import secrets
import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)
from main import  get_bot_settings,get_premium_plan
async def show_info(query):
    user = query.from_user
    settings = await get_bot_settings()
    plan = await get_premium_plan()
    
    info_text = (
        "ℹ️ <b>Информация об AlertMe</b>\n\n"
        f"<b>💎 Premium подписка:</b>\n"
        f"• Цена: {plan.price_stars} Telegram Stars\n"
        f"• Срок: {settings.subscription_days} дней\n\n"
        f"<b>Возможности Premium:</b>\n"
        f"✅ Неограниченные контакты\n"
        f"✅ Геозоны\n"
        f"✅ История местоположений\n"
        f"✅ Приоритетная поддержка\n\n"
    )
    
    if user.username:
        info_text += (
            f"<b>📱 Ваш Telegram:</b>\n"
            f"@{user.username}\n\n"
            f"Используйте его в приложении для получения SOS уведомлений!\n\n"
        )
    
    info_text += (
        f"<b>🚨 SOS Уведомления:</b>\n"
        f"При активации SOS близкими вы получите:\n"
        f"• Уведомление с координатами\n"
        f"• Ссылку на карту\n"
        f"• Время активации\n"
        f"• Аудио запись (если доступно)"
    )
    
    keyboard = [[InlineKeyboardButton("« Назад", callback_data='back_to_menu')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.message.edit_text(info_text, parse_mode='HTML', reply_markup=reply_markup)


# ==================== UTILITIES ====================

def generate_activation_code():
    """Генерация уникального кода активации"""
    parts = [secrets.token_hex(2).upper() for _ in range(3)]
    return '-'.join(parts)
