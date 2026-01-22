import logging
import requests
import uuid
from django.conf import settings
from typing import Optional, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class NikitaSMSService:
    """SMS сервис через smspro.nikita.kg"""
    
    def __init__(self):
        self.api_url = 'https://smspro.nikita.kg/api/message'
        self.dr_url = 'https://smspro.nikita.kg/api/dr'
        
        # Получаем настройки из settings.py
        self.login = getattr(settings, 'NIKITA_SMS_LOGIN', None)
        self.password = getattr(settings, 'NIKITA_SMS_PASSWORD', None)
        self.sender = getattr(settings, 'NIKITA_SMS_SENDER', 'AlertMe')
        
        self.enabled = bool(self.login and self.password)
        
        if self.enabled:
            logger.info(f"✅ Nikita SMS сервис активирован (отправитель: {self.sender})")
        else:
            logger.warning("⚠️ Nikita SMS сервис отключен - не указаны NIKITA_SMS_LOGIN/PASSWORD")
    
    def _normalize_phone(self, phone: str) -> str:
        """
        Нормализация номера телефона для КР
        +996 550 40 39 93 -> 996550403993
        """
        # Убираем все символы кроме цифр
        phone = ''.join(filter(str.isdigit, phone))
        
        # Если начинается с 996, оставляем как есть
        if phone.startswith('996'):
            return phone
        
        # Если начинается с 0, заменяем на 996
        if phone.startswith('0'):
            return '996' + phone[1:]
        
        # Если короткий номер, добавляем 996
        if len(phone) == 9:
            return '996' + phone
        
        return phone
    
    def _generate_transaction_id(self) -> str:
        """Генерация уникального ID транзакции"""
        return str(uuid.uuid4())[:8]
    
    def send_sms(
        self,
        to_phone: str,
        message: str,
        test: bool = False
    ) -> Dict[str, Any]:
        """
        Отправка SMS через Nikita API
        
        Args:
            to_phone: Номер телефона получателя
            message: Текст сообщения (до 800 символов)
            test: Если True - тестовая отправка (не тарифицируется)
        
        Returns:
            Dict с результатом отправки
        """
        if not self.enabled:
            logger.warning("❌ SMS отправка невозможна - сервис отключен")
            return {
                'success': False,
                'error': 'SMS service disabled',
                'fallback': 'console'
            }
        
        try:
            # Нормализуем номер
            normalized_phone = self._normalize_phone(to_phone)
            
            # Проверяем, что номер из КР (996)
            if not normalized_phone.startswith('996'):
                logger.warning(f"⚠️ Номер {to_phone} не из КР, SMS не отправлен")
                return {
                    'success': False,
                    'error': 'Only KG numbers supported (996)',
                    'phone': to_phone
                }
            
            # Генерируем ID транзакции
            transaction_id = self._generate_transaction_id()
            
            # Формируем XML запрос
            test_tag = '<test>1</test>' if test else ''
            
            xml_data = f"""<?xml version="1.0" encoding="UTF-8"?>
<message>
    <login>{self.login}</login>
    <pwd>{self.password}</pwd>
    <id>{transaction_id}</id>
    <sender>{self.sender}</sender>
    <text>{self._escape_xml(message)}</text>
    <phones>
        <phone>{normalized_phone}</phone>
    </phones>
    {test_tag}
</message>"""
            
            logger.info(f"📤 Отправка SMS на {normalized_phone} (ID: {transaction_id})")
            if test:
                logger.info("🧪 ТЕСТОВАЯ отправка (не тарифицируется)")
            
            # Отправляем запрос
            response = requests.post(
                self.api_url,
                data=xml_data.encode('utf-8'),
                headers={'Content-Type': 'application/xml; charset=utf-8'},
                timeout=10
            )
            
            logger.info(f"📥 Ответ сервера: {response.status_code}")
            logger.debug(f"Response: {response.text}")
            
            if response.status_code == 200:
                # Парсим ответ
                response_text = response.text
                
                # Проверяем на ошибки в ответе
                if 'error' in response_text.lower():
                    logger.error(f"❌ Ошибка API: {response_text}")
                    return {
                        'success': False,
                        'error': response_text,
                        'transaction_id': transaction_id,
                        'phone': normalized_phone
                    }
                
                logger.info(f"✅ SMS отправлен успешно на {normalized_phone}")
                return {
                    'success': True,
                    'transaction_id': transaction_id,
                    'phone': normalized_phone,
                    'response': response_text,
                    'test': test
                }
            else:
                logger.error(f"❌ Ошибка HTTP: {response.status_code}")
                return {
                    'success': False,
                    'error': f'HTTP {response.status_code}',
                    'transaction_id': transaction_id,
                    'phone': normalized_phone
                }
        
        except requests.RequestException as e:
            logger.error(f"❌ Ошибка сети при отправке SMS: {e}")
            return {
                'success': False,
                'error': f'Network error: {str(e)}',
                'phone': to_phone
            }
        except Exception as e:
            logger.error(f"❌ Неожиданная ошибка при отправке SMS: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'phone': to_phone
            }
    
    def send_bulk_sms(
        self,
        phones: list[str],
        message: str,
        test: bool = False
    ) -> Dict[str, Any]:
        """
        Отправка SMS на несколько номеров одним запросом
        
        Args:
            phones: Список номеров телефонов
            message: Текст сообщения
            test: Тестовая отправка
        
        Returns:
            Dict с результатом отправки
        """
        if not self.enabled:
            logger.warning("❌ SMS отправка невозможна - сервис отключен")
            return {'success': False, 'error': 'SMS service disabled'}
        
        try:
            # Нормализуем все номера
            normalized_phones = [self._normalize_phone(p) for p in phones]
            
            # Оставляем только номера КР
            kg_phones = [p for p in normalized_phones if p.startswith('996')]
            
            if not kg_phones:
                logger.warning("⚠️ Нет номеров из КР в списке")
                return {
                    'success': False,
                    'error': 'No KG numbers in list',
                    'total': len(phones)
                }
            
            transaction_id = self._generate_transaction_id()
            
            # Формируем XML с несколькими телефонами
            phones_xml = ''.join([f'<phone>{phone}</phone>' for phone in kg_phones])
            test_tag = '<test>1</test>' if test else ''
            
            xml_data = f"""<?xml version="1.0" encoding="UTF-8"?>
<message>
    <login>{self.login}</login>
    <pwd>{self.password}</pwd>
    <id>{transaction_id}</id>
    <sender>{self.sender}</sender>
    <text>{self._escape_xml(message)}</text>
    <phones>
        {phones_xml}
    </phones>
    {test_tag}
</message>"""
            
            logger.info(f"📤 Массовая отправка SMS на {len(kg_phones)} номеров (ID: {transaction_id})")
            
            response = requests.post(
                self.api_url,
                data=xml_data.encode('utf-8'),
                headers={'Content-Type': 'application/xml; charset=utf-8'},
                timeout=15
            )
            
            if response.status_code == 200:
                logger.info(f"✅ Массовая отправка выполнена: {len(kg_phones)} номеров")
                return {
                    'success': True,
                    'transaction_id': transaction_id,
                    'phones': kg_phones,
                    'count': len(kg_phones),
                    'response': response.text,
                    'test': test
                }
            else:
                logger.error(f"❌ Ошибка массовой отправки: {response.status_code}")
                return {
                    'success': False,
                    'error': f'HTTP {response.status_code}',
                    'transaction_id': transaction_id
                }
        
        except Exception as e:
            logger.error(f"❌ Ошибка массовой отправки SMS: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_delivery_report(self, transaction_id: str, phone: Optional[str] = None) -> Dict[str, Any]:
        """
        Получение отчета о доставке SMS
        
        Args:
            transaction_id: ID транзакции
            phone: Опционально - номер телефона для фильтрации
        
        Returns:
            Dict с отчетом о доставке
        """
        if not self.enabled:
            return {'success': False, 'error': 'SMS service disabled'}
        
        try:
            phone_tag = f'<phone>{self._normalize_phone(phone)}</phone>' if phone else ''
            
            xml_data = f"""<?xml version="1.0" encoding="UTF-8"?>
<dr>
    <login>{self.login}</login>
    <pwd>{self.password}</pwd>
    <id>{transaction_id}</id>
    {phone_tag}
</dr>"""
            
            response = requests.post(
                self.dr_url,
                data=xml_data.encode('utf-8'),
                headers={'Content-Type': 'application/xml; charset=utf-8'},
                timeout=10
            )
            
            if response.status_code == 200:
                return {
                    'success': True,
                    'transaction_id': transaction_id,
                    'report': response.text
                }
            else:
                return {
                    'success': False,
                    'error': f'HTTP {response.status_code}',
                    'transaction_id': transaction_id
                }
        
        except Exception as e:
            logger.error(f"❌ Ошибка получения отчета: {e}")
            return {
                'success': False,
                'error': str(e),
                'transaction_id': transaction_id
            }
    
    def _escape_xml(self, text: str) -> str:
        """Экранирование спецсимволов XML"""
        return (text
            .replace('&', '&amp;')
            .replace('<', '&lt;')
            .replace('>', '&gt;')
            .replace('"', '&quot;')
            .replace("'", '&apos;')
        )