import logging
from django.conf import settings
from typing import Optional, Dict, Any
from notifications.nikita_sms_service import NikitaSMSService

logger = logging.getLogger(__name__)


class SMSService:
    """
    Универсальный SMS сервис
    - Использует реальную отправку через Nikita SMS для номеров КР (996)
    - Fallback в консоль для других номеров или при ошибках
    """
    
    def __init__(self):
        self.nikita_sms = NikitaSMSService()
        
        if self.nikita_sms.enabled:
            logger.info("✅ SMS сервис: Nikita SMS (реальная отправка)")
        else:
            logger.info("📱 SMS сервис: Консоль (Nikita SMS отключен)")
    
    def send_sms(
        self,
        to_phone: str,
        message: str,
        media_urls: Optional[list] = None
    ) -> bool:
        """
        Отправка SMS с автоматическим выбором метода
        
        Args:
            to_phone: Номер телефона
            message: Текст сообщения
            media_urls: Ссылки на медиа (добавляются в конец сообщения)
        
        Returns:
            True если успешно
        """
        # Добавляем медиа ссылки в сообщение
        full_message = message
        if media_urls:
            full_message += "\n\n🎬 Медиа:\n" + "\n".join(media_urls)
        
        # Тестовый режим: не отправляем через Nikita, только вывод в консоль
        if getattr(settings, 'SMS_VERIFICATION_TEST_MODE', False):
            logger.info("🧪 Тестовый режим SMS включен — Nikita не используется")
            return self._send_via_console(to_phone, full_message, media_urls)
        
        # Пытаемся отправить через Nikita SMS
        if self.nikita_sms.enabled:
            result = self.nikita_sms.send_sms(
                to_phone=to_phone,
                message=full_message,
                test=False  # Реальная отправка
            )
            
            if result['success']:
                logger.info(f"✅ SMS отправлен через Nikita API: {to_phone}")
                return True
            else:
                logger.warning(f"⚠️ Nikita SMS ошибка: {result.get('error')}")
                # Fallback в консоль
                return self._send_via_console(to_phone, full_message, media_urls)
        
        # Если Nikita SMS отключен - консоль
        return self._send_via_console(to_phone, full_message, media_urls)
    
    def send_bulk_sms(
        self,
        phones: list[str],
        message: str
    ) -> Dict[str, Any]:
        """
        Массовая отправка SMS
        
        Args:
            phones: Список номеров
            message: Текст сообщения
        
        Returns:
            Dict с результатами
        """
        if self.nikita_sms.enabled:
            return self.nikita_sms.send_bulk_sms(
                phones=phones,
                message=message,
                test=False
            )
        else:
            # Fallback - отправка по одному в консоль
            success_count = 0
            for phone in phones:
                if self._send_via_console(phone, message):
                    success_count += 1
            
            return {
                'success': success_count > 0,
                'count': success_count,
                'total': len(phones)
            }
    
    def _send_via_console(
        self, 
        to_phone: str, 
        message: str,
        media_urls: Optional[list] = None
    ) -> bool:
        """Вывод SMS в консоль для тестирования"""
        print("\n" + "="*70)
        print("📱 SMS СООБЩЕНИЕ (КОНСОЛЬ)")
        print("="*70)
        print(f"📞 Кому: {to_phone}")
        print(f"\n📨 Текст:")
        print("-" * 70)
        for line in message.split('\n'):
            print(f"   {line}")
        print("-" * 70)
        
        if media_urls:
            print(f"\n🎬 Медиа файлы:")
            for url in media_urls:
                print(f"   • {url}")
        
        print("="*70 + "\n")
        
        logger.info(f"📱 SMS выведен в консоль для {to_phone}")
        return True