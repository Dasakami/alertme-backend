import logging
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from django.utils.html import strip_tags
from typing import Optional, List
import os

logger = logging.getLogger(__name__)


class EmailService:
    @staticmethod
    def send_sos_email(
        to_emails: List[str],
        user_name: str,
        latitude: float = None,
        longitude: float = None,
        address: str = None,
        sos_alert_id: int = None,
        audio_file_path: str = None,
        video_file_path: str = None,
    ) -> bool:
        try:
            google_maps_url = None
            media_url = None
            
            if latitude and longitude:
                google_maps_url = (
                    f"https://www.google.com/maps/search/?api=1"
                    f"&query={latitude},{longitude}"
                )
            
            if sos_alert_id:
                base_url = getattr(settings, 'SITE_URL', 'https://alertme-ihww.onrender.com').rstrip('/')
                media_url = f"{base_url}/api/media/sos/{sos_alert_id}/"
            context = {
                'user_name': user_name,
                'address': address or 'Неизвестно',
                'latitude': latitude,
                'longitude': longitude,
                'google_maps_url': google_maps_url,
                'media_url': media_url,
                'has_audio': bool(audio_file_path),
                'has_video': bool(video_file_path),
                'timestamp': None, 
            }
            html_content = render_to_string(
                'notifications/sos_email.html',
                context
            )
            text_content = strip_tags(html_content)
            subject = f'🚨 ЭКСТРЕННАЯ ТРЕВОГА от {user_name}!'
            
            email = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=to_emails,
            )
            email.attach_alternative(html_content, "text/html")
            if audio_file_path and os.path.exists(audio_file_path):
                with open(audio_file_path, 'rb') as f:
                    email.attach(
                        filename=f'sos_audio_{sos_alert_id}.aac',
                        content=f.read(),
                        mimetype='audio/aac'
                    )
                logger.info(f"📎 Аудио прикреплено к email")
            if video_file_path and os.path.exists(video_file_path):
                with open(video_file_path, 'rb') as f:
                    email.attach(
                        filename=f'sos_video_{sos_alert_id}.mp4',
                        content=f.read(),
                        mimetype='video/mp4'
                    )
                logger.info(f"📎 Видео прикреплено к email")
            email.send(fail_silently=False)
            
            logger.info(
                f" SOS email отправлен на {len(to_emails)} адресов: "
                f"{', '.join(to_emails)}"
            )
            return True
            
        except Exception as e:
            logger.error(f" Ошибка отправки SOS email: {e}", exc_info=True)
            return False
    
    @staticmethod
    def send_test_email(to_email: str) -> bool:
        try:
            subject = 'AlertMe - Тест Email'
            message = 'Это тестовое сообщение из AlertMe. Email работает!'
            
            from django.core.mail import send_mail
            
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[to_email],
                fail_silently=False,
            )
            
            logger.info(f" Тестовый email отправлен на {to_email}")
            return True
            
        except Exception as e:
            logger.error(f" Ошибка отправки тестового email: {e}", exc_info=True)
            return False