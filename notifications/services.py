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
    
    def send_sms(
        self, 
        to_phone: str, 
        message: str,
        telegram_username: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Отправка SMS через Twilio или Telegram
        
        Args:
            to_phone: Номер телефона в формате +996...
            message: Текст сообщения
            telegram_username: Username в Telegram (для fallback)
        
        Returns:
            {
                'success': bool,
                'method': 'twilio' | 'telegram' | 'failed',
                'message_id': str | None,
                'error': str | None
            }
        """
        # Пробуем Twilio (если настроен)
        if self.twilio_enabled:
            try:
                sms = self.twilio_client.messages.create(
                    body=message,
                    from_=settings.TWILIO_PHONE_NUMBER,
                    to=to_phone
                )
                
                logger.info(f"✅ SMS отправлено через Twilio: {to_phone}")
                return {
                    'success': True,
                    'method': 'twilio',
                    'message_id': sms.sid,
                    'error': None
                }
            except Exception as e:
                logger.error(f"❌ Ошибка Twilio SMS: {e}")
                # Не падаем, пробуем Telegram fallback
        
        # Fallback на Telegram
        if self.telegram_enabled and telegram_username:
            try:
                result = self._send_telegram_notification(
                    telegram_username, 
                    f"📱 SMS для {to_phone}:\n\n{message}"
                )
                
                if result['success']:
                    logger.info(f"✅ Уведомление отправлено через Telegram: @{telegram_username}")
                    return {
                        'success': True,
                        'method': 'telegram',
                        'message_id': result.get('message_id'),
                        'error': None
                    }
            except Exception as e:
                logger.error(f"❌ Ошибка Telegram: {e}")
        
        # Если ничего не сработало
        logger.error(f"❌ Не удалось отправить уведомление на {to_phone}")
        return {
            'success': False,
            'method': 'failed',
            'message_id': None,
            'error': 'No delivery method available'
        }
    
    def make_call(
        self, 
        to_phone: str,
        telegram_username: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Звонок через Twilio или уведомление в Telegram
        
        Args:
            to_phone: Номер телефона
            telegram_username: Username в Telegram (для fallback)
        
        Returns:
            {
                'success': bool,
                'method': 'twilio' | 'telegram' | 'failed',
                'call_id': str | None,
                'error': str | None
            }
        """
        # Пробуем Twilio
        if self.twilio_enabled:
            try:
                call = self.twilio_client.calls.create(
                    twiml=self._get_emergency_twiml(),
                    from_=settings.TWILIO_PHONE_NUMBER,
                    to=to_phone
                )
                
                logger.info(f"✅ Звонок совершен через Twilio: {to_phone}")
                return {
                    'success': True,
                    'method': 'twilio',
                    'call_id': call.sid,
                    'error': None
                }
            except Exception as e:
                logger.error(f"❌ Ошибка Twilio звонка: {e}")
        
        # Fallback на Telegram
        if self.telegram_enabled and telegram_username:
            try:
                result = self._send_telegram_notification(
                    telegram_username,
                    f"📞 ЭКСТРЕННЫЙ ЗВОНОК!\n\n"
                    f"Попытка позвонить на {to_phone}\n"
                    f"⚠️ ТРЕБУЕТСЯ НЕМЕДЛЕННАЯ РЕАКЦИЯ!"
                )
                
                if result['success']:
                    logger.info(f"✅ Уведомление о звонке через Telegram: @{telegram_username}")
                    return {
                        'success': True,
                        'method': 'telegram',
                        'call_id': result.get('message_id'),
                        'error': None
                    }
            except Exception as e:
                logger.error(f"❌ Ошибка Telegram: {e}")
        
        return {
            'success': False,
            'method': 'failed',
            'call_id': None,
            'error': 'No delivery method available'
        }
    
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
        
        Автоматически выбирает лучший метод доставки
        """
        # Формируем сообщение
        message = self._format_sos_message(
            user_name, latitude, longitude, address
        )
        
        # Отправляем SMS
        sms_result = self.send_sms(to_phone, message, telegram_username)
        
        # Совершаем звонок (только если это основной контакт)
        # call_result = self.make_call(to_phone, telegram_username)
        
        return {
            'sms': sms_result,
            # 'call': call_result,
            'success': sms_result['success']
        }
    
    def _send_telegram_notification(
        self, 
        username: str, 
        message: str
    ) -> Dict[str, Any]:
        """Отправка уведомления через Telegram бота"""
        try:
            # Сначала пытаемся найти chat_id по username
            chat_id = self._get_chat_id_by_username(username)
            
            if not chat_id:
                return {
                    'success': False,
                    'error': f'Chat ID not found for @{username}'
                }
            
            # Отправляем сообщение
            url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
            
            response = requests.post(url, json={
                'chat_id': chat_id,
                'text': message,
                'parse_mode': 'HTML'
            }, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                return {
                    'success': True,
                    'message_id': data['result']['message_id']
                }
            else:
                return {
                    'success': False,
                    'error': response.text
                }
        
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def _get_chat_id_by_username(self, username: str) -> Optional[int]:
        """
        Получить chat_id по username
        
        Сохраняем в Redis для кэширования
        """
        from django.core.cache import cache
        
        # Убираем @ если есть
        username = username.lstrip('@')
        
        # Проверяем кэш
        cache_key = f'telegram_chat_id:{username}'
        chat_id = cache.get(cache_key)
        
        if chat_id:
            return chat_id
        
        # Если нет в кэше, проверяем базу
        # (пользователь должен был написать боту /start)
        from notifications.models import TelegramUser
        
        try:
            tg_user = TelegramUser.objects.get(username=username)
            cache.set(cache_key, tg_user.chat_id, 3600)  # 1 час
            return tg_user.chat_id
        except TelegramUser.DoesNotExist:
            logger.warning(f"Пользователь @{username} не найден в базе")
            return None
    
    def _format_sos_message(
        self,
        user_name: str,
        latitude: float,
        longitude: float,
        address: Optional[str] = None
    ) -> str:
        """Форматирование SOS сообщения"""
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
    
    def _get_emergency_twiml(self) -> str:
        """TwiML для экстренного звонка"""
        return '''<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="alice" language="ru-RU">
        Внимание! Экстренный сигнал от приложения AlertMe. 
        Ваш близкий человек активировал тревожную кнопку. 
        Требуется немедленная помощь. 
        Проверьте местоположение в SMS сообщении.
    </Say>
    <Pause length="2"/>
    <Say voice="alice" language="ru-RU">
        Повторяю. Это экстренный сигнал. Требуется помощь.
    </Say>
</Response>'''
