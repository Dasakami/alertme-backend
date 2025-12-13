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
        
        message = f"Ваш код подтверждения: {code}\n\nSafety App"
        
        if not settings.SMS_API_KEY:
            print(f"SMS API not configured. Code: {code}")
            return False
        
        # SMS.kg API integration
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
            print(f"SMS sent to {phone}")
            return True
        else:
            print(f"SMS failed: {response.text}")
            return False
            
    except Exception as e:
        print(f"Error sending SMS: {e}")
        return False