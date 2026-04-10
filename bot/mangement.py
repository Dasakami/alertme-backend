import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, LabeledPrice
from telegram.ext import (
    ContextTypes
)
import django
from main import check_activation_code, get_user_codes 

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'AlertMe.settings')
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def prompt_activate_code(query, context):
    """Запрос кода активации"""
    await query.message.edit_text(
        "🎟️ <b>Активация кода</b>\n\n"
        "Отправьте мне код активации, полученный после оплаты.\n"
        "Формат: <code>XXXX-XXXX-XXXX</code>",
        parse_mode='HTML'
    )
    context.user_data['waiting_for_code'] = True


async def handle_code_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ввода кода"""
    if not context.user_data.get('waiting_for_code'):
        return
    
    code = update.message.text.strip().upper()
    activation = await check_activation_code(code)
    
    if activation:
        test_label = "  [Тестовый]" if activation.is_test else ""
        await update.message.reply_text(
            f" <b>Код действителен!{test_label}</b>\n\n"
            f"План: <b>{activation.plan.name}</b>\n"
            f"Статус: <b>Готов к активации</b>\n\n"
            f"📱 Введите код <code>{code}</code> в приложении AlertMe:\n"
            f"Профиль → Подписка → Активировать код",
            parse_mode='HTML'
        )
    else:
        await update.message.reply_text(
            "❌ Код не найден или уже использован.\n\n"
            "Проверьте правильность ввода или купите новый код.",
            parse_mode='HTML'
        )
    
    context.user_data['waiting_for_code'] = False


async def show_my_codes(query, context):
    """Показать коды пользователя"""
    user_id = query.from_user.id
    codes = await get_user_codes(user_id)
    
    if not codes:
        await query.message.edit_text(
            "📋 <b>Ваши коды</b>\n\n"
            "У вас пока нет кодов активации.\n"
            "Купите Premium подписку чтобы получить код!",
            parse_mode='HTML'
        )
        return
    
    text = "📋 <b>Ваши коды активации</b>\n\n"
    
    for code in codes:
        status = "✅ Активен" if not code.is_used else "✓ Использован"
        test_mark = " 🧪" if code.is_test else " 💰"
        
        text += f"{test_mark} <code>{code.code}</code>\n"
        text += f"   {status} | {code.plan.name}\n"
        text += f"   Создан: {code.created_at.strftime('%d.%m.%Y %H:%M')}\n\n"
    
    keyboard = [[InlineKeyboardButton("« Назад", callback_data='back_to_menu')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.message.edit_text(text, parse_mode='HTML', reply_markup=reply_markup)

