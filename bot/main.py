import os
import secrets
import logging
from datetime import timedelta
from telegram import Update
from telegram.ext import (
    Application, 
    CommandHandler, 
    CallbackQueryHandler, 
    MessageHandler,
    PreCheckoutQueryHandler,
    filters,
)
import django
from asgiref.sync import sync_to_async
from django.utils import timezone
from main import get_user_model

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'AlertMe.settings')
django.setup()

from subscriptions.models import ActivationCode, SubscriptionPlan, BotSettings, PaymentTransaction, UserSubscription
from notifications.models import TelegramUser
from django.contrib.auth import get_user_model
from handlers import start, button_callback, precheckout_callback,successful_payment_callback
from .mangement import handle_code_input

User = get_user_model()

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
PREMIUM_PLAN_ID = 2

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


def main():
    if not BOT_TOKEN:
        logger.error("❌ TELEGRAM_BOT_TOKEN не установлен!")
        return
    
    application = Application.builder().token(BOT_TOKEN).build()

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