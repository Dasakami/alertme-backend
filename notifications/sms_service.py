# notifications/sms_service.py
import logging
from django.conf import settings
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class SMSService:
    """
    Сервис отправки SMS через Twilio с fallback на консоль
    
    Использует:
    1. Twilio - для продакшена
    2. Console logging - для разработки/тестирования
    """
    
    def __init__(self):
        self.twilio_enabled = self._check_twilio()
        
        if self.twilio_enabled:
            from twilio.rest import Client
            self.twilio_client = Client(
                settings.TWILIO_ACCOUNT_SID,
                settings.TWILIO_AUTH_TOKEN
            )
            logger.info("✅ Twilio SMS сервис инициализирован")
        else:
            logger.warning("⚠️ Twilio не настроен - используется console fallback")
    
    def _check_twilio(self) -> bool:
        """Проверка наличия Twilio конфига"""
        return all([
            getattr(settings, 'TWILIO_ACCOUNT_SID', None),
            getattr(settings, 'TWILIO_AUTH_TOKEN', None),
            getattr(settings, 'TWILIO_PHONE_NUMBER', None),
        ])
    
    def send_sms(
        self,
        to_phone: str,
        message: str,
        media_urls: Optional[list] = None
    ) -> bool:
        """
        Отправить SMS сообщение
        
        Args:
            to_phone: Номер телефона получателя (формат: +996555123456)
            message: Текст сообщения
            media_urls: Список URL для MMS (опционально)
        
        Returns:
            True если успешно, False если ошибка
        """
        try:
            if self.twilio_enabled:
                return self._send_via_twilio(to_phone, message, media_urls)
            else:
                return self._send_via_console(to_phone, message)
        except Exception as e:
            logger.error(f"❌ Ошибка отправки SMS: {e}", exc_info=True)
            return False
    
    def _send_via_twilio(
        self,
        to_phone: str,
        message: str,
        media_urls: Optional[list] = None
    ) -> bool:
        """Отправка через Twilio"""
        try:
            # Форматируем номер
            if not to_phone.startswith('+'):
                to_phone = '+' + to_phone
            
            if media_urls:
                # MMS отправка
                sms = self.twilio_client.messages.create(
                    body=message,
                    from_=settings.TWILIO_PHONE_NUMBER,
                    to=to_phone,
                    media_url=media_urls
                )
            else:
                # SMS отправка
                sms = self.twilio_client.messages.create(
                    body=message,
                    from_=settings.TWILIO_PHONE_NUMBER,
                    to=to_phone
                )
            # Логируем детали ответа Twilio
            sid = getattr(sms, 'sid', None)
            status = getattr(sms, 'status', None)
            error_code = getattr(sms, 'error_code', None)
            error_message = getattr(sms, 'error_message', None)

            logger.info(
                f"✅ Twilio response: to={to_phone} sid={sid} status={status} "
                f"error_code={error_code} error_message={error_message}"
            )

            # Считаем успешной отправку, если error_code пуст
            if error_code:
                logger.error(f"❌ Twilio reported error for {to_phone}: {error_code} {error_message}")
                return False

            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка Twilio: {e}", exc_info=True)
            return False
    
    def _send_via_console(self, to_phone: str, message: str) -> bool:
        """Fallback отправка в консоль (для разработки)"""
        print("\n" + "="*60)
        print("📱 SMS СООБЩЕНИЕ (CONSOLE MODE - Twilio не настроен)")
        print("="*60)
        print(f"📞 Кому: {to_phone}")
        print(f"📨 Текст:")
        print(f"   {message}")
        print("="*60 + "\n")
        
        logger.info(f"📱 SMS в консоль на {to_phone}")
        return True
