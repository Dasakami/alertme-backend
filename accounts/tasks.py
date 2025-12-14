from celery import shared_task
from django.conf import settings
import requests


@shared_task
def send_verification_sms(sms_verification_id):
    """Send SMS verification code"""
    from .models import SMSVerification
    
    try:
        sms_verification = SMSVerification.objects.get(id=sms_verification_id)
        
        phone = str(sms_verification.phone_number)
        code = sms_verification.code
        
        # ═══════════════════════════════════════════════════════════
        # ПОКА ПРОСТО ВЫВОДИМ В КОНСОЛЬ
        # ═══════════════════════════════════════════════════════════
        print(f"")
        print(f"═════════════════════════════════════════════")
        print(f"📱 SMS КОД ДЛЯ: {phone}")
        print(f"🔐 КОД: {code}")
        print(f"⏰ Действителен 10 минут")
        print(f"═════════════════════════════════════════════")
        print(f"")
        
        # ВРЕМЕННО ОТКЛЮЧЕНО - когда купите SMS API, раскомментируйте:
        """
        if not settings.SMS_API_KEY:
            return False
        
        message = f"Ваш код подтверждения: {code}\n\nSafety App"
        
        response = requests.post(
            settings.SMS_API_URL,
            json={
                'key': settings.SMS_API_KEY,
                'phone': phone,
                'message': message,
            },
            timeout=10
        )
        
        if response.status_code == 200:
            print(f"✅ SMS отправлен на {phone}")
            return True
        else:
            print(f"❌ SMS ошибка: {response.text}")
            return False
        """
        
        return True  # Возвращаем успех для тестового режима
            
    except Exception as e:
        print(f"❌ Ошибка отправки SMS: {e}")
        return False