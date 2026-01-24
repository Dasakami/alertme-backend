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
from django.contrib.auth import get_user_model

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'AlertMe.settings')
django.setup()

from subscriptions.models import ActivationCode, SubscriptionPlan, BotSettings, PaymentTransaction, UserSubscription
from notifications.models import TelegramUser
from django.contrib.auth import get_user_model
from handlers import start, button_callback, precheckout_callback,successful_payment_callback
from mangement import handle_code_input
from bot_utils import save_telegram_user, get_bot_settings, is_user_admin, get_premium_plan, create_activation_code, create_payment_transaction, check_activation_code, get_user_codes

User = get_user_model()

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8423156547:AAHvgLbi5syDqaf5iWlvg82QU0qsHN5BEUs")
PREMIUM_PLAN_ID = 2


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