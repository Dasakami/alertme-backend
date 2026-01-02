import os
import logging
from django.conf import settings
from typing import Optional, Dict, Any
import requests

logger = logging.getLogger(__name__)


class NotificationService:
    """
    Универсальная система уведомлений с Twilio и Telegram fallback
    
    Логика работы:
    1. Если TWILIO настроен - используем Twilio (продакшн)
    2. Если TWILIO не настроен - используем Telegram бота (MVP/демо)
    """
    
    def __init__(self):
        self.twilio_enabled = self._check_twilio()
        self.telegram_enabled = self._check_telegram()
        
        if self.twilio_enabled:
            from twilio.rest import Client
            self.twilio_client = Client(
                settings.TWILIO_ACCOUNT_SID,
                settings.TWILIO_AUTH_TOKEN
            )
            logger.info("✅ Twilio включен (продакшн режим)")
        elif self.telegram_enabled:
            logger.info("✅ Telegram fallback включен (MVP режим)")
        else:
            logger.warning("⚠️ Нет настроенных сервисов уведомлений")
    
    def _check_twilio(self) -> bool:
        """Проверка настроек Twilio"""
        return all([
            getattr(settings, 'TWILIO_ACCOUNT_SID', None),
            getattr(settings, 'TWILIO_AUTH_TOKEN', None),
            getattr(settings, 'TWILIO_PHONE_NUMBER', None),
        ])
    
    def _check_telegram(self) -> bool:
        """Проверка настроек Telegram"""
        return bool(getattr(settings, 'TELEGRAM_BOT_TOKEN', None))
    
    def send_sos_alert(
        self,
        to_phone: str,
        user_name: str,
        latitude: float,
        longitude: float,
        address: Optional[str] = None,
        telegram_username: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Отправка экстренного SOS уведомления
        
        Args:
            to_phone: Номер телефона контакта
            user_name: Имя пользователя активировавшего SOS
            latitude: Широта
            longitude: Долгота
            address: Адрес (опционально)
            telegram_username: Username контакта в Telegram (для fallback)
        """
        message = self._format_sos_message(
            user_name, latitude, longitude, address
        )
        
        # Приоритет 1: Twilio SMS
        if self.twilio_enabled:
            try:
                sms = self.twilio_client.messages.create(
                    body=message,
                    from_=settings.TWILIO_PHONE_NUMBER,
                    to=to_phone
                )
                
                logger.info(f"✅ SOS отправлено через Twilio: {to_phone}")
                return {
                    'success': True,
                    'method': 'twilio',
                    'message_id': sms.sid,
                }
            except Exception as e:
                logger.error(f"❌ Ошибка Twilio: {e}")
        
        # Приоритет 2: Telegram
        if self.telegram_enabled and telegram_username:
            result = self._send_telegram_sos(
                telegram_username,
                user_name,
                latitude,
                longitude,
                address
            )
            
            if result['success']:
                logger.info(f"✅ SOS отправлено в Telegram: @{telegram_username}")
                return result
        
        # Не удалось отправить
        logger.error(f"❌ Не удалось отправить SOS уведомление")
        return {
            'success': False,
            'method': 'failed',
            'error': 'No delivery method available'
        }
    
    def _send_telegram_sos(
        self,
        username: str,
        user_name: str,
        latitude: float,
        longitude: float,
        address: Optional[str] = None
    ) -> Dict[str, Any]:
        """Отправка SOS через Telegram с красивым форматированием"""
        try:
            # Получаем chat_id по username
            chat_id = self._get_chat_id_by_username(username)
            
            if not chat_id:
                return {
                    'success': False,
                    'error': f'Пользователь @{username} не найден. '
                             'Попросите его написать /start боту.'
                }
            
            # Google Maps ссылка
            google_maps_url = (
                f"https://www.google.com/maps/search/?api=1"
                f"&query={latitude},{longitude}"
            )
            
            # Форматируем сообщение
            from datetime import datetime
            message = (
                "🚨 <b>ЭКСТРЕННАЯ ТРЕВОГА!</b>\n\n"
                f"<b>{user_name}</b> активировал SOS!\n\n"
                f"📍 <b>Местоположение:</b>\n"
                f"<a href='{google_maps_url}'>Открыть на карте</a>\n\n"
            )
            
            if address:
                message += f"📮 <b>Адрес:</b> {address}\n\n"
            
            message += (
                f"⏰ <b>Время:</b> {datetime.now().strftime('%H:%M, %d.%m.%Y')}\n\n"
                f"❗ Это автоматическое уведомление из приложения AlertMe"
            )
            
            # Отправляем сообщение
            url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
            
            response = requests.post(url, json={
                'chat_id': chat_id,
                'text': message,
                'parse_mode': 'HTML',
                'disable_web_page_preview': False
            }, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                return {
                    'success': True,
                    'method': 'telegram',
                    'message_id': data['result']['message_id']
                }
            else:
                logger.error(f"Telegram API error: {response.text}")
                return {
                    'success': False,
                    'error': f'Telegram API error: {response.status_code}'
                }
        
        except Exception as e:
            logger.error(f"Ошибка отправки в Telegram: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e)
            }
    
    def _get_chat_id_by_username(self, username: str) -> Optional[int]:
        """
        Получить chat_id по username из базы данных
        
        Пользователь должен был написать /start боту
        """
        from django.core.cache import cache
        from notifications.models import TelegramUser
        
        # Убираем @ если есть
        username = username.lstrip('@')
        
        # Проверяем кэш
        cache_key = f'telegram_chat_id:{username}'
        chat_id = cache.get(cache_key)
        
        if chat_id:
            return chat_id
        
        # Ищем в базе
        try:
            tg_user = TelegramUser.objects.get(
                username__iexact=username,
                is_active=True
            )
            # Кэшируем на 1 час
            cache.set(cache_key, tg_user.chat_id, 3600)
            return tg_user.chat_id
        except TelegramUser.DoesNotExist:
            logger.warning(
                f"Пользователь @{username} не найден в базе. "
                f"Попросите его написать /start боту."
            )
            return None
    
    def _format_sos_message(
        self,
        user_name: str,
        latitude: float,
        longitude: float,
        address: Optional[str] = None
    ) -> str:
        """Форматирование SOS сообщения для SMS"""
        message = f"🚨 ЭКСТРЕННАЯ ТРЕВОГА!\n\n"
        message += f"{user_name} активировал SOS!\n\n"
        
        google_maps_url = (
            f"https://www.google.com/maps/search/?api=1"
            f"&query={latitude},{longitude}"
        )
        
        message += f"📍 Местоположение:\n{google_maps_url}\n\n"
        
        if address:
            message += f"Адрес: {address}\n\n"
        
        from datetime import datetime
        message += f"⏰ Время: {datetime.now().strftime('%H:%M, %d.%m.%Y')}\n\n"
        message += "❗ Это автоматическое сообщение из приложения AlertMe"
        
        return message
    
    def send_audio_to_telegram(
        self,
        telegram_username: str,
        audio_path: str,
        caption: Optional[str] = None
    ) -> bool:
        """Отправка аудио в Telegram"""
        try:
            # Получаем chat_id по username
            chat_id = self._get_chat_id_by_username(telegram_username)
            
            if not chat_id:
                logger.warning(
                    f"Пользователь @{telegram_username} не найден. "
                    f"Попросите его написать /start боту."
                )
                return False
            
            # Отправляем аудио
            import requests
            
            url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendAudio"
            
            with open(audio_path, 'rb') as audio_file:
                files = {'audio': audio_file}
                data = {'chat_id': chat_id}
                
                if caption:
                    data['caption'] = caption
                
                response = requests.post(url, files=files, data=data, timeout=30)
                
                if response.status_code == 200:
                    logger.info(f"✅ Аудио отправлено @{telegram_username} (chat_id: {chat_id})")
                    return True
                else:
                    logger.error(f"❌ Ошибка Telegram API: {response.text}")
                    return False
                    
        except Exception as e:
            logger.error(f"❌ Ошибка отправки аудио: {e}", exc_info=True)
            return False