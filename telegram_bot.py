import os
import secrets
import logging
from datetime import timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, LabeledPrice
from telegram.ext import (
    Application, 
    CommandHandler, 
    CallbackQueryHandler, 
    MessageHandler,
    PreCheckoutQueryHandler,
    filters,
    ContextTypes
)
import django
from asgiref.sync import sync_to_async
from django.utils import timezone

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'AlertMe.settings')
django.setup()

from subscriptions.models import ActivationCode, SubscriptionPlan, BotSettings, PaymentTransaction, UserSubscription
from notifications.models import TelegramUser
from django.contrib.auth import get_user_model

User = get_user_model()

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Конфигурация
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8423156547:AAGZC3tBsLbAzLYGVt2_rzDd8nJhAPsNP48")
PREMIUM_PLAN_ID = 2

# ==================== DATABASE HELPERS ====================

@sync_to_async
def save_telegram_user(chat_id, user_id, username, first_name, last_name):
    """Сохранение информации о пользователе Telegram"""
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
def get_bot_settings():
    """Получить настройки бота"""
    return BotSettings.get_settings()


@sync_to_async
def is_user_admin(telegram_user_id):
    """Проверка, является ли пользователь админом"""
    settings = BotSettings.get_settings()
    return settings.is_admin(telegram_user_id)


@sync_to_async
def get_premium_plan():
    """Получить Premium план"""
    try:
        return SubscriptionPlan.objects.get(id=PREMIUM_PLAN_ID)
    except SubscriptionPlan.DoesNotExist:
        return SubscriptionPlan.objects.create(
            id=PREMIUM_PLAN_ID,
            name='Premium',
            plan_type='personal_premium',
            description='Premium подписка',
            price_monthly=100,
            price_stars=100,
            max_contacts=999,
            geozones_enabled=True,
            location_history_enabled=True
        )


@sync_to_async
def create_activation_code(code, plan, user_id, is_test=False, payment_transaction=None):
    """Создание кода активации"""
    settings = BotSettings.get_settings()
    
    activation_code = ActivationCode.objects.create(
        code=code,
        plan=plan,
        telegram_user_id=user_id,
        payment_amount=plan.price_stars,
        is_active=True,
        is_test=is_test,
        payment_transaction=payment_transaction,
        expires_at=timezone.now() + timedelta(hours=settings.code_expiration_hours)
    )
    
    # Обновляем статистику
    settings.total_codes_generated += 1
    settings.save(update_fields=['total_codes_generated'])
    
    return activation_code


@sync_to_async
def check_activation_code(code):
    """Проверка кода активации"""
    try:
        return ActivationCode.objects.select_related('plan').get(
            code=code,
            is_active=True,
            is_used=False
        )
    except ActivationCode.DoesNotExist:
        return None


@sync_to_async
def create_payment_transaction(user_id, plan, telegram_payment_charge_id=None):
    """Создание транзакции оплаты"""
    try:
        # Получаем или создаем пользователя Django по Telegram ID
        telegram_user = TelegramUser.objects.filter(chat_id=user_id).first()
        
        # Создаем временную подписку для транзакции
        django_user = User.objects.first()  # Fallback пользователь
        if telegram_user and hasattr(telegram_user, 'user'):
            django_user = telegram_user.user
        
        subscription, _ = UserSubscription.objects.get_or_create(
            user=django_user,
            defaults={
                'plan': plan,
                'status': 'pending',
                'payment_period': 'monthly',
                'start_date': timezone.now(),
                'end_date': timezone.now() + timedelta(days=30)
            }
        )
        
        transaction = PaymentTransaction.objects.create(
            user=django_user,
            subscription=subscription,
            amount=plan.price_stars,
            currency='XTR',  # Telegram Stars
            payment_method='telegram_stars',
            transaction_id=f'TG_{telegram_payment_charge_id or secrets.token_hex(8)}',
            telegram_payment_charge_id=telegram_payment_charge_id,
            telegram_user_id=user_id,
            status='completed' if telegram_payment_charge_id else 'pending'
        )
        
        if telegram_payment_charge_id:
            settings = BotSettings.get_settings()
            settings.total_payments_received += 1
            settings.save(update_fields=['total_payments_received'])
        
        return transaction
        
    except Exception as e:
        logger.error(f"❌ Ошибка создания транзакции: {e}", exc_info=True)
        return None


@sync_to_async
def get_user_codes(telegram_user_id):
    """Получить коды пользователя"""
    codes = ActivationCode.objects.filter(
        telegram_user_id=telegram_user_id
    ).order_by('-created_at')[:10]
    return list(codes)


# ==================== BOT HANDLERS ====================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /start"""
    user = update.effective_user
    chat_id = update.effective_chat.id
    
    created = await save_telegram_user(
        chat_id, user.id, user.username, user.first_name, user.last_name
    )
    
    if created:
        logger.info(f"✅ Новый пользователь: @{user.username} (ID: {user.id})")
    
    # Проверяем, является ли пользователь админом
    is_admin = await is_user_admin(user.id)
    settings = await get_bot_settings()
    
    # Формируем клавиатуру
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
    """Обработка нажатий на кнопки"""
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


# ==================== PAYMENT HANDLERS ====================

async def show_payment(query, context):
    """Показать страницу оплаты"""
    is_admin = await is_user_admin(query.from_user.id)
    settings = await get_bot_settings()
    plan = await get_premium_plan()
    
    keyboard = [
        [InlineKeyboardButton(f"💳 Оплатить {plan.price_stars} ⭐", callback_data='confirm_payment')],
    ]
    
    # Админы могут генерировать тестовые коды
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
    
    # Создаем invoice для оплаты Stars
    title = "AlertMe Premium"
    description = f"Premium подписка на {settings.subscription_days} дней"
    payload = f"premium_{query.from_user.id}_{secrets.token_hex(4)}"
    currency = "XTR"  # Telegram Stars
    prices = [LabeledPrice("Premium подписка", plan.price_stars)]
    
    try:
        await context.bot.send_invoice(
            chat_id=query.message.chat_id,
            title=title,
            description=description,
            payload=payload,
            provider_token="",  # Пустой для Stars
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


# ==================== CODE MANAGEMENT ====================

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
        test_label = " 🧪 [Тестовый]" if activation.is_test else ""
        await update.message.reply_text(
            f"✅ <b>Код действителен!{test_label}</b>\n\n"
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


# ==================== ADMIN PANEL ====================

async def show_admin_panel(query, context):
    """Админ панель"""
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


# ==================== INFO ====================

async def show_info(query):
    """Информация о боте"""
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


# ==================== MAIN ====================

def main():
    """Запуск бота"""
    if not BOT_TOKEN:
        logger.error("❌ TELEGRAM_BOT_TOKEN не установлен!")
        return
    
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_callback))
    application.add_handler(PreCheckoutQueryHandler(precheckout_callback))
    application.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_code_input))
    
    logger.info("=" * 50)
    logger.info("🤖 AlertMe Telegram Bot запущен!")
    logger.info("💎 Production режим с реальными платежами")
    logger.info("🧪 Админы могут создавать тестовые коды")
    logger.info("🚨 Готов отправлять SOS уведомления")
    logger.info("=" * 50)
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()