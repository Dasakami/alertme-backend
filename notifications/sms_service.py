import logging
from django.conf import settings
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class SMSService:
    
    def __init__(self):
        # ВРЕМЕННО: Всегда используем консоль
        self.twilio_enabled = False
        logger.info("📱 SMS сервис в режиме консоли (Twilio отключен)")
    
    def send_sms(
        self,
        to_phone: str,
        message: str,
        media_urls: Optional[list] = None
    ) -> bool:
        try:
            # Всегда отправляем в консоль
            return self._send_via_console(to_phone, message, media_urls)
        except Exception as e:
            logger.error(f"❌ Ошибка отправки SMS: {e}", exc_info=True)
            return False
    
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