# telegram_notification_bot.py - ОБНОВЛЕННЫЙ БОТ
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

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'AlertMe.settings')
django.setup()

from subscriptions.models import ActivationCode, SubscriptionPlan
from notifications.models import TelegramUser

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

BOT_TOKEN = "7205482794:AAFstGWp1aOoLS_L_TNVX74aQzgwGDgKQy8"
PREMIUM_PLAN_ID = 2
PRICE_IN_STARS = 100


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /start"""
    user = update.effective_user
    
    # Сохраняем пользователя в базу для уведомлений
    try:
        telegram_user, created = TelegramUser.objects.update_or_create(
            chat_id=user.id,
            defaults={
                'username': user.username,
                'first_name': user.first_name,
                'last_name': user.last_name,
            }
        )
        
        if created:
            logger.info(f"✅ Новый пользователь зарегистрирован: @{user.username} (ID: {user.id})")
    except Exception as e:
        logger.error(f"❌ Ошибка сохранения пользователя: {e}")
    
    keyboard = [
        [InlineKeyboardButton("💎 Купить Premium (100 ⭐)", callback_data='buy_premium')],
        [InlineKeyboardButton("🔑 Активировать код", callback_data='activate_code')],
        [InlineKeyboardButton("ℹ️ Информация", callback_data='info')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🛡️ <b>AlertMe Bot</b>\n\n"
        "👋 Добро пожаловать!\n\n"
        "<b>Этот бот используется для:</b>\n"
        "• Покупки Premium подписки\n"
        "• Получения экстренных уведомлений (если у ваших близких нет Twilio)\n\n"
        "💡 Чтобы получать SOS уведомления, сообщите свой username близким:\n"
        f"<code>@{user.username or 'ваш_username'}</code>\n\n"
        "Выберите действие:",
        parse_mode='HTML',
        reply_markup=reply_markup
    )


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка нажатий на кнопки"""
    query = update.callback_query
    await query.answer()
    
    if query.data == 'buy_premium':
        await show_payment(query, context)
    elif query.data == 'activate_code':
        await query.message.reply_text(
            "🔑 <b>Активация кода</b>\n\n"
            "Отправьте мне код активации, полученный после оплаты.\n"
            "Формат: <code>XXXX-XXXX-XXXX</code>",
            parse_mode='HTML'
        )
        context.user_data['waiting_for_code'] = True
    elif query.data == 'info':
        user = query.from_user
        await query.message.reply_text(
            "ℹ️ <b>Информация</b>\n\n"
            f"Ваш Telegram ID: <code>{user.id}</code>\n"
            f"Username: @{user.username or 'не указан'}\n\n"
            "<b>О Premium:</b>\n"
            "💎 Стоимость: 100 Telegram Stars\n"
            "⏰ Период: 30 дней\n\n"
            "<b>Возможности:</b>\n"
            "• Неограниченные контакты\n"
            "• Геозоны\n"
            "• История местоположений\n"
            "• Приоритетная поддержка\n\n"
            "<b>SOS Уведомления:</b>\n"
            "Если у вас нет Twilio, уведомления будут приходить сюда!",
            parse_mode='HTML'
        )
    elif query.data == 'confirm_payment':
        await process_payment(query, context)
    elif query.data == 'back_to_menu':
        await start_from_callback(query, context)


async def start_from_callback(query, context):
    """Возврат в главное меню из callback"""
    keyboard = [
        [InlineKeyboardButton("💎 Купить Premium (100 ⭐)", callback_data='buy_premium')],
        [InlineKeyboardButton("🔑 Активировать код", callback_data='activate_code')],
        [InlineKeyboardButton("ℹ️ Информация", callback_data='info')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.message.edit_text(
        "🛡️ <b>AlertMe Bot</b>\n\n"
        "Выберите действие:",
        parse_mode='HTML',
        reply_markup=reply_markup
    )


async def show_payment(query, context):
    """Показываем информацию об оплате"""
    keyboard = [
        [InlineKeyboardButton("✅ Оплатить 100 ⭐", callback_data='confirm_payment')],
        [InlineKeyboardButton("« Назад", callback_data='back_to_menu')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.message.edit_text(
        "💳 <b>Оплата Premium подписки</b>\n\n"
        "Стоимость: <b>100 Telegram Stars</b> ⭐\n"
        "Срок: <b>30 дней</b>\n\n"
        "После оплаты вы мгновенно получите код активации.\n"
        "Введите этот код в приложении AlertMe.\n\n"
        "⚠️ <i>Для MVP: Оплата симулируется, код выдается сразу</i>",
        parse_mode='HTML',
        reply_markup=reply_markup
    )


async def process_payment(query, context):
    """Обработка оплаты"""
    user_id = query.from_user.id
    
    try:
        # Генерируем код
        code = generate_activation_code()
        
        # Получаем Premium план
        try:
            plan = SubscriptionPlan.objects.get(id=PREMIUM_PLAN_ID)
        except SubscriptionPlan.DoesNotExist:
            # Создаем план если его нет
            plan = SubscriptionPlan.objects.create(
                id=PREMIUM_PLAN_ID,
                name='Premium',
                plan_type='personal_premium',
                description='Premium подписка',
                price_monthly=100,
                max_contacts=999,
                geozones_enabled=True,
                location_history_enabled=True
            )
        
        # Создаем код активации
        activation_code = ActivationCode.objects.create(
            code=code,
            plan=plan,
            telegram_user_id=user_id,
            payment_amount=PRICE_IN_STARS,
            is_active=True
        )
        
        await query.message.edit_text(
            "✅ <b>Оплата успешна!</b>\n\n"
            f"Ваш код активации:\n\n"
            f"<code>{code}</code>\n\n"
            "📱 <b>Как активировать:</b>\n"
            "1. Откройте приложение AlertMe\n"
            "2. Перейдите в Настройки → Подписка\n"
            "3. Нажмите \"Активировать код\"\n"
            "4. Введите этот код\n\n"
            "⏰ Код действителен 24 часа.",
            parse_mode='HTML'
        )
        
        logger.info(f"✅ Создан код активации {code} для пользователя {user_id}")
        
    except Exception as e:
        logger.error(f"❌ Ошибка создания кода: {e}", exc_info=True)
        await query.message.edit_text(
            "❌ Произошла ошибка при создании кода.\n\n"
            f"Детали ошибки: {str(e)}\n\n"
            "Пожалуйста, попробуйте еще раз или обратитесь в поддержку.",
            parse_mode='HTML'
        )


async def handle_code_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ввода кода активации"""
    if not context.user_data.get('waiting_for_code'):
        return
    
    code = update.message.text.strip().upper()
    
    try:
        activation = ActivationCode.objects.get(
            code=code,
            is_active=True,
            is_used=False
        )
        
        await update.message.reply_text(
            f"✅ <b>Код действителен!</b>\n\n"
            f"План: <b>{activation.plan.name}</b>\n"
            f"Статус: <b>Готов к активации</b>\n\n"
            f"Введите этот код в приложении для активации подписки.",
            parse_mode='HTML'
        )
        
    except ActivationCode.DoesNotExist:
        await update.message.reply_text(
            "❌ Код не найден или уже использован.\n\n"
            "Проверьте правильность ввода или купите новый.",
            parse_mode='HTML'
        )
    
    context.user_data['waiting_for_code'] = False


def generate_activation_code():
    """Генерация кода формата XXXX-XXXX-XXXX"""
    parts = [secrets.token_hex(2).upper() for _ in range(3)]
    return '-'.join(parts)


def main():
    """Запуск бота"""
    if not BOT_TOKEN:
        print("❌ TELEGRAM_BOT_TOKEN не установлен в переменных окружения!")
        return
    
    application = Application.builder().token(BOT_TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_code_input))
    
    logger.info("🤖 Бот запущен и готов к работе!")
    logger.info("📱 Отправляет уведомления через Telegram (если Twilio не настроен)")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()