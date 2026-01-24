import secrets
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, LabeledPrice
from telegram.ext import (
    ContextTypes
)

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)
from bot_utils import is_user_admin, get_bot_settings,get_premium_plan, save_telegram_user, create_activation_code,create_payment_transaction
from admin import show_admin_panel,show_admin_stats, generate_test_code
from mangement import show_my_codes, prompt_activate_code
from info_and_utils import generate_activation_code, show_info
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat_id = update.effective_chat.id
    
    created = await save_telegram_user(
        chat_id, user.id, user.username, user.first_name, user.last_name
    )
    
    if created:
        logger.info(f"✅ Новый пользователь: @{user.username} (ID: {user.id})")
    
    is_admin = await is_user_admin(user.id)
    settings = await get_bot_settings()
    
    keyboard = []
    
    if is_admin:
        keyboard.append([InlineKeyboardButton("👑 АДМИН ПАНЕЛЬ", callback_data='admin_panel')])
    
    keyboard.extend([
        [InlineKeyboardButton(f"💎 Купить Premium ({settings.default_price_stars} ⭐)", callback_data='buy_premium')],
        [InlineKeyboardButton("🎟️ Активировать код", callback_data='activate_code')],
        [InlineKeyboardButton("📋 Мои коды", callback_data='my_codes')],
        [InlineKeyboardButton("ℹ️ Информация", callback_data='info')],
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    admin_label = " 👑 [АДМИН]" if is_admin else ""
    
    welcome_text = (
        f"🛡️ <b>AlertMe Bot{admin_label}</b>\n\n"
        "Добро пожаловать!\n\n"
        "<b>Этот бот используется для:</b>\n"
        "• 💎 Покупки Premium подписки\n"
        "• 🚨 Получения экстренных SOS уведомлений\n"
        "• 📍 Уведомлений о местоположении близких\n\n"
    )
    
    if user.username:
        welcome_text += (
            "<b>📱 Как получать уведомления:</b>\n"
            f"1. В приложении AlertMe зайдите в Профиль\n"
            f"2. Введите ваш Telegram: <code>@{user.username}</code>\n"
            f"3. Добавьте близких с их Telegram username\n"
            f"4. При SOS вы получите уведомление!\n\n"
        )
    else:
        welcome_text += (
            "⚠️ <b>У вас нет username в Telegram!</b>\n"
            "Установите его в настройках для получения уведомлений.\n\n"
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
        await prompt_activate_code(query, context)
    elif query.data == 'info':
        await show_info(query)
    elif query.data == 'my_codes':
        await show_my_codes(query, context)
    elif query.data == 'admin_panel':
        await show_admin_panel(query, context)
    elif query.data == 'admin_test_code':
        await generate_test_code(query, context)
    elif query.data == 'admin_stats':
        await show_admin_stats(query, context)
    elif query.data == 'confirm_payment':
        await process_payment_invoice(query, context)
    elif query.data == 'back_to_menu':
        await back_to_start(query, context)


async def back_to_start(query, context):
    """Возврат в главное меню"""
    user = query.from_user
    is_admin = await is_user_admin(user.id)
    settings = await get_bot_settings()
    
    keyboard = []
    if is_admin:
        keyboard.append([InlineKeyboardButton("👑 АДМИН ПАНЕЛЬ", callback_data='admin_panel')])
    
    keyboard.extend([
        [InlineKeyboardButton(f"💎 Купить Premium ({settings.default_price_stars} ⭐)", callback_data='buy_premium')],
        [InlineKeyboardButton("🎟️ Активировать код", callback_data='activate_code')],
        [InlineKeyboardButton("📋 Мои коды", callback_data='my_codes')],
        [InlineKeyboardButton("ℹ️ Информация", callback_data='info')],
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.message.edit_text(
        "🛡️ <b>AlertMe Bot</b>\n\nВыберите действие:",
        parse_mode='HTML',
        reply_markup=reply_markup
    )


async def show_payment(query, context):
    """Показать страницу оплаты"""
    is_admin = await is_user_admin(query.from_user.id)
    settings = await get_bot_settings()
    plan = await get_premium_plan()
    
    keyboard = [
        [InlineKeyboardButton(f"💳 Оплатить {plan.price_stars} ⭐", callback_data='confirm_payment')],
    ]
    
    if is_admin:
        keyboard.append([InlineKeyboardButton("🧪 Создать тестовый код (БЕСПЛАТНО)", callback_data='admin_test_code')])
    
    keyboard.append([InlineKeyboardButton("« Назад", callback_data='back_to_menu')])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    mode_info = ""
    if is_admin:
        mode_info = "\n\n👑 <b>Вы администратор</b>\nМожете создавать тестовые коды бесплатно"
    
    await query.message.edit_text(
        f"💳 <b>Premium подписка AlertMe</b>\n\n"
        f"💰 Стоимость: <b>{plan.price_stars} Telegram Stars</b> ⭐\n"
        f"⏰ Срок: <b>{settings.subscription_days} дней</b>\n\n"
        f"<b>Что вы получите:</b>\n"
        f"✅ Неограниченные экстренные контакты\n"
        f"✅ Геозоны (безопасные/опасные зоны)\n"
        f"✅ История местоположений\n"
        f"✅ Приоритетная поддержка\n\n"
        f"После оплаты вы получите код активации для приложения.{mode_info}",
        parse_mode='HTML',
        reply_markup=reply_markup
    )


async def process_payment_invoice(query, context):
    """Создание инвойса для оплаты через Telegram Stars"""
    plan = await get_premium_plan()
    settings = await get_bot_settings()
    
    title = "AlertMe Premium"
    description = f"Premium подписка на {settings.subscription_days} дней"
    payload = f"premium_{query.from_user.id}_{secrets.token_hex(4)}"
    currency = "XTR"
    prices = [LabeledPrice("Premium подписка", plan.price_stars)]
    
    try:
        await context.bot.send_invoice(
            chat_id=query.message.chat_id,
            title=title,
            description=description,
            payload=payload,
            provider_token="",  
            currency=currency,
            prices=prices,
            max_tip_amount=0,
            need_name=False,
            need_phone_number=False,
            need_email=False,
            need_shipping_address=False,
            is_flexible=False
        )
        
        await query.message.reply_text(
            "💳 Инвойс отправлен!\n\n"
            "Нажмите кнопку 'Pay' чтобы оплатить через Telegram Stars.",
            parse_mode='HTML'
        )
        
    except Exception as e:
        logger.error(f"❌ Ошибка создания инвойса: {e}", exc_info=True)
        await query.message.reply_text(
            "❌ Ошибка создания инвойса.\n\n"
            "Попробуйте позже или обратитесь в поддержку.",
            parse_mode='HTML'
        )


async def precheckout_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Предпроверка платежа"""
    query = update.pre_checkout_query
    await query.answer(ok=True)


async def successful_payment_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка успешного платежа"""
    payment = update.message.successful_payment
    user_id = update.effective_user.id
    
    logger.info(f"✅ Успешный платеж от {user_id}: {payment.telegram_payment_charge_id}")
    
    try:
        plan = await get_premium_plan()
        
        # Создаем транзакцию
        transaction = await create_payment_transaction(
            user_id, plan, payment.telegram_payment_charge_id
        )
        
        # Генерируем код активации
        code = generate_activation_code()
        activation_code = await create_activation_code(
            code, plan, user_id, is_test=False, payment_transaction=transaction
        )
        
        settings = await get_bot_settings()
        
        await update.message.reply_text(
            f"🎉 <b>Оплата успешна!</b>\n\n"
            f"Ваш код активации:\n\n"
            f"<code>{code}</code>\n\n"
            f"📱 <b>Как активировать:</b>\n"
            f"1. Откройте приложение AlertMe\n"
            f"2. Профиль → Подписка\n"
            f"3. Нажмите \"Активировать код\"\n"
            f"4. Введите код: <code>{code}</code>\n\n"
            f"⏰ Код действителен {settings.code_expiration_hours} часов\n\n"
            f"💡 Нажмите на код чтобы скопировать!",
            parse_mode='HTML'
        )
        
        logger.info(f"✅ Код {code} выдан пользователю {user_id}")
        
    except Exception as e:
        logger.error(f"❌ Ошибка при обработке платежа: {e}", exc_info=True)
        await update.message.reply_text(
            "❌ Произошла ошибка при создании кода.\n\n"
            "Платеж прошел успешно. Обратитесь в поддержку для получения кода.",
            parse_mode='HTML'
        )
