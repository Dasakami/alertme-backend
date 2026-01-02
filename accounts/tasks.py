from django.conf import settings
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)


def send_verification_sms(sms_verification_id):
    """Отправка SMS кода подтверждения через Twilio (синхронная)"""
    from .models import SMSVerification
    from notifications.sms_service import SMSService
    
    try:
        sms_verification = SMSVerification.objects.get(id=sms_verification_id)
        phone = str(sms_verification.phone_number)
        code = sms_verification.code
        
        # Используем SMS сервис
        sms_service = SMSService()
        
        message = f"Ваш код подтверждения AlertMe: {code}\nДействителен 10 минут"
        
        success = sms_service.send_sms(
            to_phone=phone,
            message=message
        )
        
        if success:
            logger.info(f"✅ Код подтверждения отправлен на {phone}")
            return True
        else:
            logger.error(f"❌ Не удалось отправить SMS на {phone}")
            return False
            
    except SMSVerification.DoesNotExist:
        logger.error(f"❌ SMSVerification с ID {sms_verification_id} не найдена")
        return False
    except Exception as e:
        logger.error(f"❌ Ошибка отправки SMS: {e}", exc_info=True)
        return False


def cleanup_expired_verifications():
    """Очистка истекших кодов подтверждения"""
    from .models import SMSVerification
    
    expired_count, _ = SMSVerification.objects.filter(
        expires_at__lt=timezone.now(),
        is_verified=False
    ).delete()
    
    logger.info(f"✅ Удалено {expired_count} истекших кодов подтверждения")