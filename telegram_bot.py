import os
import secrets
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, 
    CommandHandler, 
    CallbackQueryHandler, 
    MessageHandler,
    filters,
    ContextTypes
)
import django
from asgiref.sync import sync_to_async

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'AlertMe.settings')
django.setup()

from subscriptions.models import ActivationCode, SubscriptionPlan
from notifications.models import TelegramUser

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

BOT_TOKEN = "8423156547:AAGZC3tBsLbAzLYGVt2_rzDd8nJhAPsNP48"
PREMIUM_PLAN_ID = 2
PRICE_IN_STARS = 100
@sync_to_async
def save_telegram_user(chat_id, username, first_name, last_name):
    try:
        telegram_user, created = TelegramUser.objects.update_or_create(
            chat_id=chat_id,
            defaults={
                'username': username,
                'first_name': first_name,
                'last_name': last_name,
            }
        )
        return created
    except Exception as e:
        logger.error(f"❌ Ошибка сохранения пользователя: {e}")
        return False


@sync_to_async
def get_premium_plan():
    try:
        return SubscriptionPlan.objects.get(id=PREMIUM_PLAN_ID)
    except SubscriptionPlan.DoesNotExist:
        return SubscriptionPlan.objects.create(
            id=PREMIUM_PLAN_ID,
            name='Premium',
            plan_type='personal_premium',
            description='Premium подписка',
            price_monthly=100,
            max_contacts=999,
            geozones_enabled=True,
            location_history_enabled=True
        )


@sync_to_async
def create_activation_code(code, plan, user_id):
    return ActivationCode.objects.create(
        code=code,
        plan=plan,
        telegram_user_id=user_id,
        payment_amount=PRICE_IN_STARS,
        is_active=True
    )


@sync_to_async
def check_activation_code(code):
    try:
        return ActivationCode.objects.get(
            code=code,
            is_active=True,
            is_used=False
        )
    except ActivationCode.DoesNotExist:
        return None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /start"""
    user = update.effective_user
    chat_id = update.effective_chat.id 
    
    created = await save_telegram_user(
        chat_id,  
        user.username,
        user.first_name,
        user.last_name
    )
    
    if created:
        logger.info(f"Новый пользователь: @{user.username} (ID: {user.id}, Chat: {chat_id})")
    
    keyboard = [
        [InlineKeyboardButton("Купить Premium (100 ⭐)", callback_data='buy_premium')],
        [InlineKeyboardButton("Активировать код", callback_data='activate_code')],
        [InlineKeyboardButton("Информация", callback_data='info')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    welcome_text = (
        " <b>AlertMe Bot</b>\n\n"
        " Добро пожаловать!\n\n"
        "<b>Этот бот используется для:</b>\n"
        "• Покупки Premium подписки\n"
        "• Получения экстренных SOS уведомлений\n\n"
    )
    
    if user.username:
        welcome_text += (
            "<b>Как получать уведомления:</b>\n"
            f"1. В приложении AlertMe зайдите в Профиль\n"
            f"2. Введите ваш Telegram username: <code>@{user.username}</code>\n"
            f"3. Добавьте близких в Emergency контакты с их Telegram username\n"
            f"4. При SOS уведомления (+ аудио) придут в Telegram!\n\n"
            f" Ваш Chat ID: <code>{chat_id}</code>\n\n"
        )
    else:
        welcome_text += (
            " У вас нет username в Telegram!\n"
            "Установите его в настройках Telegram, чтобы получать уведомления.\n\n"
        )
    
    welcome_text += "Выберите действие:"
    
    await update.message.reply_text(
        welcome_text,
        parse_mode='HTML',
        reply_markup=reply_markup
    )


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == 'buy_premium':
        await show_payment(query, context)
    elif query.data == 'activate_code':
        await query.message.reply_text(
            " <b>Активация кода</b>\n\n"
            "Отправьте мне код активации, полученный после оплаты.\n"
            "Формат: <code>XXXX-XXXX-XXXX</code>",
            parse_mode='HTML'
        )
        context.user_data['waiting_for_code'] = True
    elif query.data == 'info':
        await show_info(query)
    elif query.data == 'confirm_payment':
        await process_payment(query, context)
    elif query.data == 'back_to_menu':
        await start_from_callback(query, context)


async def start_from_callback(query, context):
    user = query.from_user
    keyboard = [
        [InlineKeyboardButton(" Купить Premium (100 ⭐)", callback_data='buy_premium')],
        [InlineKeyboardButton(" Активировать код", callback_data='activate_code')],
        [InlineKeyboardButton(" Информация", callback_data='info')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.message.edit_text(
        "🛡️ <b>AlertMe Bot</b>\n\n"
        "Выберите действие:",
        parse_mode='HTML',
        reply_markup=reply_markup
    )


async def show_info(query):
    user = query.from_user
    
    info_text = (
        "<b>Информация</b>\n\n"
        f"Ваш Telegram ID: <code>{user.id}</code>\n"
    )
    
    if user.username:
        info_text += f"Username: @{user.username}\n\n"
    else:
        info_text += "Username: <i>не установлен</i>\n\n"
    
    info_text += (
        "<b>О Premium:</b>\n"
        "💎 Стоимость: 100 Telegram Stars\n"
        "⏰ Период: 30 дней\n\n"
        "<b>Возможности:</b>\n"
        "• Неограниченные контакты\n"
        "• Геозоны\n"
        "• История местоположений\n"
        "• Приоритетная поддержка\n\n"
        "<b>SOS Уведомления:</b>\n"
        "При активации SOS близкими, вы получите:\n"
        "• 🚨 Уведомление с координатами\n"
        "• 🗺️ Ссылку на карту\n"
        "• ⏰ Время активации\n"
    )
    
    await query.message.edit_text(info_text, parse_mode='HTML')


async def show_payment(query, context):
    keyboard = [
        [InlineKeyboardButton(" Оплатить 100 ⭐", callback_data='confirm_payment')],
        [InlineKeyboardButton("« Назад", callback_data='back_to_menu')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.message.edit_text(
        "💳 <b>Оплата Premium подписки</b>\n\n"
        "Стоимость: <b>100 Telegram Stars</b> ⭐\n"
        "Срок: <b>30 дней</b>\n\n"
        "<b>Что вы получите:</b>\n"
        "✅ Неограниченные экстренные контакты\n"
        "✅ Геозоны (безопасные/опасные зоны)\n"
        "✅ История местоположений\n"
        "✅ Приоритетная поддержка\n\n"
        "После оплаты вы получите код активации.\n"
        "Введите его в приложении AlertMe.\n\n"
        "⚠️ <i>Для демо: код выдается сразу</i>",
        parse_mode='HTML',
        reply_markup=reply_markup
    )


async def process_payment(query, context):
    """Обработка оплаты и создание кода"""
    user_id = query.from_user.id
    
    try:
        code = generate_activation_code()
        plan = await get_premium_plan()
        await create_activation_code(code, plan, user_id)
        
        await query.message.edit_text(
            "<b>Оплата успешна!</b>\n\n"
            f"Ваш код активации:\n\n"
            f"<code>{code}</code>\n\n"
            "📱 <b>Как активировать:</b>\n"
            "1. Откройте приложение AlertMe\n"
            "2. Перейдите в Профиль → Подписка\n"
            "3. Нажмите \"Активировать код\"\n"
            "4. Введите этот код\n\n"
            "Код действителен 24 часа.\n\n"
            " Совет: Скопируйте код прямо сейчас!",
            parse_mode='HTML'
        )
        
        logger.info(f"Код {code} создан для пользователя {user_id}")
        
    except Exception as e:
        logger.error(f"Ошибка создания кода: {e}", exc_info=True)
        await query.message.edit_text(
            "Произошла ошибка при создании кода.\n\n"
            "Пожалуйста, попробуйте еще раз или обратитесь в поддержку:\n"
            "@your_support_username",
            parse_mode='HTML'
        )


async def handle_code_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get('waiting_for_code'):
        return
    
    code = update.message.text.strip().upper()
    
    activation = await check_activation_code(code)
    
    if activation:
        await update.message.reply_text(
            f"<b>Код действителен!</b>\n\n"
            f"План: <b>Premium</b>\n"
            f"Статус: <b>Готов к активации</b>\n\n"
            f"Введите код <code>{code}</code> в приложении AlertMe "
            f"в разделе Профиль → Подписка.",
            parse_mode='HTML'
        )
    else:
        await update.message.reply_text(
            " Код не найден или уже использован.\n\n"
            "Проверьте правильность ввода или купите новый код.",
            parse_mode='HTML'
        )
    
    context.user_data['waiting_for_code'] = False


def generate_activation_code():
    parts = [secrets.token_hex(2).upper() for _ in range(3)]
    return '-'.join(parts)


def main():
    if not BOT_TOKEN:
        logger.error(" TELEGRAM_BOT_TOKEN не установлен!")
        return
    
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_code_input))
    
    logger.info("Бот запущен и готов к работе!")
    logger.info("Готов отправлять SOS уведомления")
    logger.info("Готов продавать Premium подписки")
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()